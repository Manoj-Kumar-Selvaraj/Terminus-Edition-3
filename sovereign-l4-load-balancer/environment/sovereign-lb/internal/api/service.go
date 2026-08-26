package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"sovereign-lb/internal/audit"
	"sovereign-lb/internal/catalog"
	"sovereign-lb/internal/fleet"
	"sovereign-lb/internal/health"
	"sovereign-lb/internal/metrics"
	"sovereign-lb/internal/model"
	"sovereign-lb/internal/nodes"
	"sovereign-lb/internal/ops"
	"sovereign-lb/internal/readiness"
	"sovereign-lb/internal/recovery"
	"sovereign-lb/internal/retention"
	"sovereign-lb/internal/revision"
	"sovereign-lb/internal/rollout"
	"sovereign-lb/internal/snapshot"
)

type Service struct {
	mutex          sync.RWMutex
	repository     *snapshot.Repository
	revisions      *revision.Store
	nodes          *nodes.Registry
	rollout        *rollout.Coordinator
	audit          *audit.Ring
	metrics        *metrics.Registry
	desired        *model.Desired
	active         uint64
	sessions       map[string]*nodeSession
	readiness      *readiness.Evaluator
	retention      *retention.Manager
	health         *health.Aggregator
	fleet          fleet.Inventory
	profiles       map[string]fleet.NodeProfile
	scenarios      []catalog.Scenario
	recoveryReport recovery.Report
	configRoot     string
}

func Open(root string) (*Service, error) {
	bootstrap, err := recovery.Open(root)
	if err != nil {
		return nil, err
	}
	report, err := bootstrap.Recover()
	if err != nil {
		return nil, fmt.Errorf("recovery bootstrap: %w", err)
	}
	if err := bootstrap.ValidateAuthority(); err != nil {
		return nil, fmt.Errorf("authority validation: %w", err)
	}
	if err := bootstrap.AlignActive(report); err != nil {
		return nil, fmt.Errorf("recovery alignment: %w", err)
	}
	registry := nodes.NewRegistry()
	active := report.ActiveGeneration
	evaluator := readiness.New(bootstrap.Repository, registry)
	evaluator.SetActive(active)
	retentionLimit := 8
	if current, currentErr := bootstrap.Repository.Current(); currentErr == nil && current.Snapshot.Limits.RetainedGenerations > 0 {
		retentionLimit = current.Snapshot.Limits.RetainedGenerations
	}
	retentionManager := retention.New(bootstrap.Repository, retentionLimit)
	if active > 0 {
		retentionManager.Acquire(active, "control-plane")
	}
	aggregator := health.New(64)
	service := &Service{
		repository:     bootstrap.Repository,
		revisions:      bootstrap.Revisions,
		nodes:          registry,
		rollout:        rollout.NewCoordinator(registry, active),
		audit:          audit.New(4096),
		metrics:        metrics.New(),
		active:         active,
		sessions:       map[string]*nodeSession{},
		readiness:      evaluator,
		retention:      retentionManager,
		health:         aggregator,
		profiles:       map[string]fleet.NodeProfile{},
		recoveryReport: report,
	}
	service.loadOperatorSurface(root)
	return service, nil
}

func (service *Service) loadOperatorSurface(stateRoot string) {
	configRoot := discoverConfigRoot(stateRoot)
	service.configRoot = configRoot
	if configRoot == "" {
		return
	}
	inventoryPath := filepath.Join(configRoot, "config", "fleet.json")
	if inventory, err := fleet.LoadInventory(inventoryPath); err == nil {
		service.fleet = inventory
		service.readiness.SetInventory(inventory)
		if profiles, profileErr := fleet.LoadAllProfiles(configRoot, inventory); profileErr == nil {
			service.profiles = profiles
			for _, profile := range profiles {
				_ = fleet.EnsureNodeStateRoot(profile)
			}
		}
	}
	scenarioRoot := filepath.Join(configRoot, "config", "scenarios")
	if scenarios, err := catalog.LoadDirectory(scenarioRoot); err == nil {
		service.scenarios = scenarios
	}
}

func discoverConfigRoot(stateRoot string) string {
	if home := strings.TrimSpace(os.Getenv("SOVEREIGN_LB_HOME")); home != "" {
		return home
	}
	candidate := filepath.Clean(filepath.Join(stateRoot, "..", ".."))
	if _, err := os.Stat(filepath.Join(candidate, "config", "fleet.json")); err == nil {
		return candidate
	}
	return ""
}

func (service *Service) Apply(body []byte, key string, now time.Time) ([]byte, int, error) {
	if key == "" || len(key) > 128 {
		return nil, http.StatusBadRequest, errors.New("invalid idempotency key")
	}
	var desired model.Desired
	decoder := json.NewDecoder(strings.NewReader(string(body)))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&desired); err != nil {
		return nil, http.StatusBadRequest, err
	}
	if err := model.ValidateDesired(desired); err != nil {
		return nil, http.StatusUnprocessableEntity, err
	}
	requestDigest := revision.Digest(body)
	generation, replay, err := service.revisions.Begin(key, desired.Revision, requestDigest)
	if errors.Is(err, revision.ErrStale) || errors.Is(err, revision.ErrConflict) {
		return nil, http.StatusConflict, err
	}
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if replay != nil {
		return append([]byte(nil), replay.Response...), http.StatusOK, nil
	}
	compiled, err := snapshot.Compile(desired, generation, now)
	if err != nil {
		return nil, http.StatusUnprocessableEntity, err
	}
	if err := service.repository.Store(compiled); err != nil {
		return nil, http.StatusInternalServerError, err
	}
	if desired.Limits.RetainedGenerations > 0 {
		service.retention = retention.New(service.repository, desired.Limits.RetainedGenerations)
		if service.active > 0 {
			service.retention.Acquire(service.active, "control-plane")
		}
	}
	service.retention.Acquire(generation, "prepare")
	rolloutState, err := service.rollout.Begin(compiled.Snapshot, compiled.Digest, desired.Rollout, now)
	if err != nil {
		service.retention.Release(generation, "prepare")
		return nil, http.StatusConflict, err
	}
	service.dispatchPrepare(compiled)
	response, _ := json.Marshal(map[string]any{
		"revision":   desired.Revision,
		"generation": generation,
		"digest":     compiled.Digest,
		"rollout":    rolloutState.Phase,
	})
	if err := service.revisions.Commit(key, requestDigest, desired.Revision, generation, response); err != nil {
		service.retention.Release(generation, "prepare")
		return nil, http.StatusConflict, err
	}
	service.mutex.Lock()
	service.desired = &desired
	service.mutex.Unlock()
	service.metrics.Inc("sovereign_apply_total", fmt.Sprintf("generation=%d", generation))
	service.audit.Add(audit.Event{
		At: now, Actor: "operator", Operation: "apply", DigestPrefix: compiled.Digest[:12],
		Revision: desired.Revision, Generation: generation, Outcome: "accepted",
	})
	return response, http.StatusAccepted, nil
}

func (service *Service) Router() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /v1/apply", service.handleApply)
	mux.HandleFunc("GET /v1/status", service.handleStatus)
	mux.HandleFunc("GET /v1/nodes", service.handleNodes)
	mux.HandleFunc("GET /v1/audit", service.handleAudit)
	mux.HandleFunc("GET /v1/fleet", service.handleFleet)
	mux.HandleFunc("GET /v1/scenarios", service.handleScenarios)
	mux.HandleFunc("GET /v1/health", service.handleHealth)
	mux.HandleFunc("GET /v1/retention", service.handleRetention)
	mux.HandleFunc("GET /v1/recovery", service.handleRecovery)
	mux.HandleFunc("GET /ready", service.handleReady)
	mux.HandleFunc("GET /metrics", func(writer http.ResponseWriter, _ *http.Request) {
		writer.Header().Set("Content-Type", "text/plain; version=0.0.4")
		service.metrics.WriteTo(writer)
	})
	return mux
}

func (service *Service) handleApply(writer http.ResponseWriter, request *http.Request) {
	body := http.MaxBytesReader(writer, request.Body, 16<<20)
	defer body.Close()
	data, err := io.ReadAll(body)
	if err != nil {
		writeError(writer, http.StatusBadRequest, err)
		return
	}
	response, status, err := service.Apply(data, request.Header.Get("Idempotency-Key"), time.Now())
	if err != nil {
		writeError(writer, status, err)
		return
	}
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(status)
	_, _ = writer.Write(response)
}

func (service *Service) handleStatus(writer http.ResponseWriter, _ *http.Request) {
	state, present := service.rollout.Snapshot()
	service.mutex.RLock()
	active := service.active
	service.mutex.RUnlock()
	now := time.Now()
	membership := ops.ReconcileFleet(service.fleet, service.nodes, now)
	alignment := ops.GenerationAlignment(service.nodes, active, state, len(service.retention.Snapshot()))
	service.refreshHealth(now)
	writeJSON(writer, http.StatusOK, map[string]any{
		"accepted_revision":  service.revisions.AcceptedRevision(),
		"active_generation":  active,
		"rollout_present":    present,
		"rollout":            state,
		"fleet_membership":   membership,
		"generation_view":    alignment,
		"recovery":           service.recoveryReport,
		"readiness_matched":  service.readiness.MatchesRollout(state),
	})
}

func (service *Service) handleNodes(writer http.ResponseWriter, _ *http.Request) {
	writeJSON(writer, http.StatusOK, service.nodes.List())
}

func (service *Service) handleAudit(writer http.ResponseWriter, _ *http.Request) {
	events, dropped := service.audit.Snapshot()
	writeJSON(writer, http.StatusOK, map[string]any{"events": events, "dropped": dropped})
}

func (service *Service) handleFleet(writer http.ResponseWriter, _ *http.Request) {
	membership := ops.ReconcileFleet(service.fleet, service.nodes, time.Now())
	writeJSON(writer, http.StatusOK, map[string]any{
		"inventory":   service.fleet,
		"profiles":    len(service.profiles),
		"membership":  membership,
		"description": ops.DescribeMembership(membership),
		"config_root": service.configRoot,
	})
}

func (service *Service) handleScenarios(writer http.ResponseWriter, _ *http.Request) {
	writeJSON(writer, http.StatusOK, map[string]any{
		"scenarios": catalog.Summaries(service.scenarios),
		"count":     len(service.scenarios),
	})
}

func (service *Service) handleHealth(writer http.ResponseWriter, _ *http.Request) {
	now := time.Now()
	service.refreshHealth(now)
	_ = service.health.EvictStale(now)
	current := map[string]bool{}
	for _, node := range service.nodes.List() {
		if node.Connected {
			current[node.NodeID] = true
		}
	}
	writeJSON(writer, http.StatusOK, map[string]any{
		"targets": service.health.Snapshot(current),
		"summary": service.health.EffectiveSummary(current),
	})
}

func (service *Service) handleRetention(writer http.ResponseWriter, _ *http.Request) {
	writeJSON(writer, http.StatusOK, map[string]any{
		"leases": service.retention.Snapshot(),
	})
}

func (service *Service) handleRecovery(writer http.ResponseWriter, _ *http.Request) {
	writeJSON(writer, http.StatusOK, service.recoveryReport)
}

func (service *Service) handleReady(writer http.ResponseWriter, _ *http.Request) {
	state, present := service.rollout.Snapshot()
	var ready bool
	var details map[string]any
	if present {
		ready, details = service.readiness.ReadyForRollout(state)
	} else {
		ready, details = service.readiness.Ready()
	}
	status := http.StatusOK
	if !ready {
		status = http.StatusServiceUnavailable
	}
	payload := map[string]any{"ready": ready}
	for key, value := range details {
		payload[key] = value
	}
	writeJSON(writer, status, payload)
}

func (service *Service) refreshHealth(now time.Time) {
	for _, node := range service.nodes.List() {
		service.health.ObserveNode(node, now)
	}
	service.mutex.RLock()
	active := service.active
	service.mutex.RUnlock()
	if active == 0 {
		return
	}
	if compiled, err := service.repository.Load(active); err == nil {
		for _, node := range service.nodes.List() {
			if node.Connected && node.ActiveGeneration == active {
				service.health.ObserveTargets(node.NodeID, compiled.Snapshot, now)
			}
		}
	}
}

func (service *Service) promoteActive(generation uint64) {
	service.mutex.Lock()
	previous := service.active
	service.active = generation
	service.mutex.Unlock()
	service.readiness.SetActive(generation)
	if previous > 0 && previous != generation {
		service.retention.Release(previous, "control-plane")
	}
	service.retention.Acquire(generation, "control-plane")
	service.retention.Release(generation, "prepare")
	if removed, err := service.retention.Collect(generation); err == nil && len(removed) > 0 {
		service.metrics.Inc("sovereign_retention_collect_total", fmt.Sprintf("removed=%d", len(removed)))
		service.audit.Add(audit.Event{
			At: time.Now(), Actor: "retention", Operation: "collect",
			Generation: generation, Outcome: fmt.Sprintf("removed=%d", len(removed)),
		})
	}
	service.metrics.Set("sovereign_retained_leases", int64(len(service.retention.Snapshot())))
}

func writeJSON(writer http.ResponseWriter, status int, value any) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(status)
	_ = json.NewEncoder(writer).Encode(value)
}

func writeError(writer http.ResponseWriter, status int, err error) {
	writeJSON(writer, status, map[string]string{"error": err.Error()})
}

func ParseGeneration(value string) (uint64, error) {
	generation, err := strconv.ParseUint(value, 10, 64)
	if err != nil || generation == 0 {
		return 0, fmt.Errorf("invalid generation")
	}
	return generation, nil
}
