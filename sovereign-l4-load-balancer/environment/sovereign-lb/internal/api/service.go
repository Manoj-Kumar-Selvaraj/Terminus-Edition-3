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
	"sovereign-lb/internal/metrics"
	"sovereign-lb/internal/model"
	"sovereign-lb/internal/nodes"
	"sovereign-lb/internal/revision"
	"sovereign-lb/internal/rollout"
	"sovereign-lb/internal/snapshot"
)

type Service struct {
	mutex      sync.RWMutex
	repository *snapshot.Repository
	revisions  *revision.Store
	nodes      *nodes.Registry
	rollout    *rollout.Coordinator
	audit      *audit.Ring
	metrics    *metrics.Registry
	desired    *model.Desired
	active     uint64
	sessions   map[string]*nodeSession
}

func Open(root string) (*Service, error) {
	if err := os.MkdirAll(filepath.Join(root, "generations"), 0750); err != nil { return nil, err }
	revisions, err := revision.Open(root); if err != nil { return nil, err }
	repository := snapshot.NewRepository(filepath.Join(root, "generations"))
	active := uint64(0); if current, currentErr := repository.Current(); currentErr == nil { active = current.Snapshot.Generation }
	registry := nodes.NewRegistry()
	return &Service{
		repository: repository,
		revisions:  revisions,
		nodes:      registry,
		rollout:    rollout.NewCoordinator(registry, active),
		audit:      audit.New(4096),
		metrics:    metrics.New(),
		active:     active,
		sessions:   map[string]*nodeSession{},
	}, nil
}

func (service *Service) Apply(body []byte, key string, now time.Time) ([]byte, int, error) {
	if key == "" || len(key) > 128 { return nil, http.StatusBadRequest, errors.New("invalid idempotency key") }
	var desired model.Desired
	decoder := json.NewDecoder(strings.NewReader(string(body))); decoder.DisallowUnknownFields()
	if err := decoder.Decode(&desired); err != nil { return nil, http.StatusBadRequest, err }
	if err := model.ValidateDesired(desired); err != nil { return nil, http.StatusUnprocessableEntity, err }
	requestDigest := revision.Digest(body)
	generation, replay, err := service.revisions.Begin(key, desired.Revision, requestDigest)
	if errors.Is(err, revision.ErrStale) || errors.Is(err, revision.ErrConflict) { return nil, http.StatusConflict, err }
	if err != nil { return nil, http.StatusInternalServerError, err }
	if replay != nil { return append([]byte(nil), replay.Response...), http.StatusOK, nil }
	compiled, err := snapshot.Compile(desired, generation, now); if err != nil { return nil, http.StatusUnprocessableEntity, err }
	if err := service.repository.Store(compiled); err != nil { return nil, http.StatusInternalServerError, err }
	rolloutState, err := service.rollout.Begin(compiled.Snapshot, compiled.Digest, desired.Rollout, now); if err != nil { return nil, http.StatusConflict, err }
	service.dispatchPrepare(compiled)
	response, _ := json.Marshal(map[string]any{"revision": desired.Revision, "generation": generation, "digest": compiled.Digest, "rollout": rolloutState.Phase})
	if err := service.revisions.Commit(key, requestDigest, desired.Revision, generation, response); err != nil { return nil, http.StatusConflict, err }
	service.mutex.Lock(); service.desired = &desired; service.mutex.Unlock()
	service.metrics.Inc("sovereign_apply_total", fmt.Sprintf("generation=%d", generation))
	service.audit.Add(audit.Event{At: now, Actor: "operator", Operation: "apply", DigestPrefix: compiled.Digest[:12], Revision: desired.Revision, Generation: generation, Outcome: "accepted"})
	return response, http.StatusAccepted, nil
}

func (service *Service) Router() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /v1/apply", service.handleApply)
	mux.HandleFunc("GET /v1/status", service.handleStatus)
	mux.HandleFunc("GET /v1/nodes", service.handleNodes)
	mux.HandleFunc("GET /v1/audit", service.handleAudit)
	mux.HandleFunc("GET /ready", service.handleReady)
	mux.HandleFunc("GET /metrics", func(writer http.ResponseWriter, _ *http.Request) { writer.Header().Set("Content-Type", "text/plain; version=0.0.4"); service.metrics.WriteTo(writer) })
	return mux
}

func (service *Service) handleApply(writer http.ResponseWriter, request *http.Request) {
	body := http.MaxBytesReader(writer, request.Body, 16<<20); defer body.Close()
	data, err := io.ReadAll(body); if err != nil { writeError(writer, http.StatusBadRequest, err); return }
	response, status, err := service.Apply(data, request.Header.Get("Idempotency-Key"), time.Now())
	if err != nil { writeError(writer, status, err); return }
	writer.Header().Set("Content-Type", "application/json"); writer.WriteHeader(status); _, _ = writer.Write(response)
}

func (service *Service) handleStatus(writer http.ResponseWriter, _ *http.Request) { state, present := service.rollout.Snapshot(); service.mutex.RLock(); active := service.active; service.mutex.RUnlock(); writeJSON(writer, http.StatusOK, map[string]any{"accepted_revision":service.revisions.AcceptedRevision(),"active_generation":active,"rollout_present":present,"rollout":state}) }
func (service *Service) handleNodes(writer http.ResponseWriter, _ *http.Request) { writeJSON(writer, http.StatusOK, service.nodes.List()) }
func (service *Service) handleAudit(writer http.ResponseWriter, _ *http.Request) { events, dropped := service.audit.Snapshot(); writeJSON(writer, http.StatusOK, map[string]any{"events":events,"dropped":dropped}) }
func (service *Service) handleReady(writer http.ResponseWriter, _ *http.Request) { _, err := service.repository.Current(); ready := err == nil || service.revisions.AcceptedRevision() == 0; status := http.StatusOK; if !ready { status = http.StatusServiceUnavailable }; writeJSON(writer, status, map[string]bool{"ready":ready}) }
func writeJSON(writer http.ResponseWriter, status int, value any) { writer.Header().Set("Content-Type", "application/json"); writer.WriteHeader(status); _ = json.NewEncoder(writer).Encode(value) }
func writeError(writer http.ResponseWriter, status int, err error) { writeJSON(writer, status, map[string]string{"error":err.Error()}) }

func ParseGeneration(value string) (uint64, error) { generation, err := strconv.ParseUint(value, 10, 64); if err != nil || generation == 0 { return 0, fmt.Errorf("invalid generation") }; return generation, nil }