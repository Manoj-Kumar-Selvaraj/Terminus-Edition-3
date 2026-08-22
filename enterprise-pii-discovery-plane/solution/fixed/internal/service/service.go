package service

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"enterprise-pii/internal/auth"
	"enterprise-pii/internal/ingest"
	"enterprise-pii/internal/model"
	"enterprise-pii/internal/observe"
	"enterprise-pii/internal/persistence"
	"enterprise-pii/internal/protocol"
	"enterprise-pii/internal/registry"
	"enterprise-pii/internal/report"
	"enterprise-pii/internal/scheduler"
)

type Config struct {
	TenantID             string `json:"tenant_id"`
	Listen               string `json:"listen"`
	StateDir             string `json:"state_dir"`
	ReportDir            string `json:"report_dir"`
	CorpusDir            string `json:"corpus_dir"`
	PolicyFile           string `json:"policy_file"`
	SourceFile           string `json:"source_file"`
	WorkerTimeoutSeconds int    `json:"worker_timeout_seconds"`
	LeaseSeconds         int    `json:"lease_seconds"`
	RetainedGenerations  int    `json:"retained_generations"`
	RequiredWorkers      int    `json:"required_workers"`
	AuditCapacity        int    `json:"audit_capacity"`
	MetricSeriesCapacity int    `json:"metric_series_capacity"`
}

type sourceDocument struct {
	Generation string         `json:"generation"`
	Sources    []model.Source `json:"sources"`
}

type Service struct {
	Config          Config
	Sources         *registry.SourceRegistry
	Policies        *registry.PolicyRegistry
	Scheduler       *scheduler.Scheduler
	Results         *ingest.Store
	State           *persistence.Store
	Publisher       *report.Publisher
	Audit           *observe.AuditLog
	Metrics         *observe.Metrics
	Recovered       bool
	available       map[string]bool
	stateGeneration uint64
}

func Load(configPath string) (*Service, error) {
	body, err := os.ReadFile(configPath)
	if err != nil {
		return nil, err
	}
	var config Config
	if json.Unmarshal(body, &config) != nil {
		return nil, errors.New("invalid system config")
	}
	svc := &Service{
		Config:    config,
		Sources:   registry.NewSourceRegistry(),
		Policies:  registry.NewPolicyRegistry(),
		Scheduler: scheduler.New(time.Duration(config.LeaseSeconds) * time.Second),
		Results:   ingest.New(),
		State:     persistence.New(config.StateDir, config.RetainedGenerations),
		Publisher: report.NewPublisher(config.ReportDir),
		Audit:     observe.NewAudit(config.AuditCapacity),
		Metrics:   observe.NewMetrics(config.MetricSeriesCapacity),
		available: map[string]bool{},
	}
	if err = svc.loadSources(); err != nil {
		return nil, err
	}
	if err = svc.loadPolicy(); err != nil {
		return nil, err
	}
	return svc, nil
}

func (s *Service) loadSources() error {
	return s.reloadSources()
}

func (s *Service) reloadSources() error {
	body, err := os.ReadFile(s.Config.SourceFile)
	if err != nil {
		return err
	}
	var document sourceDocument
	if json.Unmarshal(body, &document) != nil {
		return errors.New("invalid source registry")
	}
	next := registry.NewSourceRegistry()
	available := map[string]bool{}
	for _, source := range document.Sources {
		source.Generation = document.Generation
		registered, err := next.Register(source)
		if err != nil {
			return err
		}
		if info, err := os.Stat(registered.CanonicalRoot); err == nil && info.IsDir() {
			available[registered.ID] = true
		}
	}
	s.Sources = next
	s.available = available
	return nil
}

func (s *Service) loadPolicy() error {
	body, err := os.ReadFile(s.Config.PolicyFile)
	if err != nil {
		return err
	}
	var policy model.Policy
	if json.Unmarshal(body, &policy) != nil {
		return errors.New("invalid policy")
	}
	_, err = s.Policies.Publish(policy, time.Now())
	return err
}

func (s *Service) Recover() error {
	generation, files, err := s.recoverStateFiles()
	if err != nil {
		if os.IsNotExist(err) {
			s.Recovered = true
			return nil
		}
		return err
	}
	if len(files) > 0 {
		if err := s.hydrate(generation, files); err != nil {
			return err
		}
	} else {
		s.stateGeneration = generation
	}
	s.Recovered = true
	s.Audit.Append(model.AuditEvent{Actor: "system", Action: "recover", Resource: "state", Outcome: "accepted"})
	return nil
}

func (s *Service) recoverStateFiles() (uint64, map[string][]byte, error) {
	if current, err := s.State.ReadCurrent(); err == nil {
		if files, loadErr := s.loadGenerationFiles(current); loadErr == nil {
			return current, files, nil
		}
	}
	return s.State.Recover()
}

func (s *Service) loadGenerationFiles(number uint64) (map[string][]byte, error) {
	path := filepath.Join(s.Config.StateDir, "generations", fmt.Sprintf("%020d", number))
	if err := s.State.VerifyPath(path); err != nil {
		return nil, err
	}
	manifestBody, err := os.ReadFile(filepath.Join(path, "manifest.json"))
	if err != nil {
		return nil, err
	}
	var manifest persistence.GenerationManifest
	if json.Unmarshal(manifestBody, &manifest) != nil {
		return nil, errors.New("invalid generation manifest")
	}
	files := map[string][]byte{}
	for _, entry := range manifest.Entries {
		content, err := os.ReadFile(filepath.Join(path, entry.Name))
		if err != nil {
			return nil, err
		}
		files[entry.Name] = content
	}
	return files, nil
}

func (s *Service) hydrate(generation uint64, files map[string][]byte) error {
	body, ok := files["snapshot.json"]
	if !ok {
		s.stateGeneration = generation
		return nil
	}
	snapshot, err := persistence.DecodeSnapshot(body)
	if err != nil {
		return err
	}
	s.stateGeneration = snapshot.Generation
	for _, policy := range snapshot.Policies {
		if _, err := s.Policies.Publish(policy, policy.PublishedAt); err != nil {
			return err
		}
	}
	for _, source := range snapshot.Sources {
		registered, err := s.Sources.Register(source)
		if err != nil {
			return err
		}
		if info, err := os.Stat(registered.CanonicalRoot); err == nil && info.IsDir() {
			s.available[registered.ID] = true
		}
	}
	s.Scheduler.Restore(snapshot.Jobs, snapshot.Shards, snapshot.Workers, snapshot.Leases)
	s.Results.Restore(snapshot.Receipts, snapshot.Findings, snapshot.Errors, snapshot.Truncations)
	s.restoreAudit(snapshot.Audit)
	s.restoreMetrics(snapshot.MetricSeries)
	return nil
}

func (s *Service) restoreAudit(events []model.AuditEvent) {
	s.Audit = observe.NewAudit(s.Config.AuditCapacity)
	for _, event := range events {
		s.Audit.Append(event)
	}
}

func (s *Service) restoreMetrics(series map[string]float64) {
	s.Metrics = observe.NewMetrics(s.Config.MetricSeriesCapacity)
	for key, value := range series {
		parts := splitMetricKey(key)
		if len(parts) == 0 {
			continue
		}
		labels := map[string]string{}
		for _, part := range parts[1:] {
			if index := indexByte(part, '='); index > 0 {
				labels[part[:index]] = part[index+1:]
			}
		}
		s.Metrics.Add(parts[0], labels, value)
	}
}

func splitMetricKey(key string) []string {
	if key == "" {
		return nil
	}
	parts := []string{}
	current := ""
	for _, ch := range key {
		if ch == ';' {
			parts = append(parts, current)
			current = ""
			continue
		}
		current += string(ch)
	}
	if current != "" {
		parts = append(parts, current)
	}
	return parts
}

func indexByte(value string, target byte) int {
	for index := 0; index < len(value); index++ {
		if value[index] == target {
			return index
		}
	}
	return -1
}

func (s *Service) buildSnapshot(now time.Time) persistence.Snapshot {
	jobs, shards, workers, leases := s.Scheduler.Export()
	receipts, findings, scanErrors, truncations := s.Results.Export()
	auditEvents, auditDropped := s.Audit.Snapshot()
	metrics, metricsDropped := s.Metrics.Snapshot()
	checkpoints := map[string]string{}
	for _, shard := range shards {
		if shard.Checkpoint != "" {
			checkpoints[shard.ID] = shard.Checkpoint
		}
	}
	if s.stateGeneration == 0 {
		s.stateGeneration = 1
	}
	return persistence.Snapshot{
		Schema:              "enterprise-pii-state/v1",
		Generation:          s.stateGeneration,
		SavedAt:             now.UTC(),
		Sources:             s.Sources.List(),
		Policies:            s.Policies.List(),
		Jobs:                jobs,
		Shards:              shards,
		Workers:             workers,
		Leases:              leases,
		Receipts:            receipts,
		Findings:            findings,
		Errors:              scanErrors,
		Truncations:         truncations,
		Checkpoints:         checkpoints,
		ReportGenerations:   map[string][]uint64{},
		RetentionLeases:     []persistence.RetentionLease{},
		Audit:               auditEvents,
		AuditDropped:        auditDropped,
		MetricSeries:        metrics,
		MetricSeriesDropped: metricsDropped,
	}
}

func (s *Service) persist(now time.Time) error {
	if err := s.reloadSources(); err != nil {
		return err
	}
	s.stateGeneration++
	snapshot := s.buildSnapshot(now)
	body, err := persistence.EncodeSnapshot(snapshot)
	if err != nil {
		return err
	}
	if err := s.State.Publish(s.stateGeneration, map[string][]byte{"snapshot.json": body}, now); err != nil {
		return err
	}
	protected := persistence.ReferencedGenerations(snapshot, now)
	_, _ = s.State.Cleanup(protected, snapshot.RetentionLeases, now)
	return nil
}

func (s *Service) CreateJob(principal model.Principal, id, policyVersion, corpusDigest string) (model.Job, error) {
	now := time.Now()
	if err := s.reloadSources(); err != nil {
		return model.Job{}, err
	}
	policy, ok := s.Policies.Get(policyVersion)
	if !ok {
		return model.Job{}, errors.New("policy not found")
	}
	sources := auth.New(s.Sources.List()).Sources(principal, "scan")
	if len(sources) == 0 {
		return model.Job{}, errors.New("no authorized sources")
	}
	job := model.Job{
		ID:               id,
		Tenant:           s.Config.TenantID,
		Generation:       uint64(now.UnixNano()),
		PolicyVersion:    policy.Version,
		PolicyDigest:     policy.Digest,
		DetectorBundle:   policy.DetectorBundle,
		CorpusDigest:     corpusDigest,
		SourceGeneration: sources[0].Generation,
	}
	if _, err := s.Scheduler.CreateJob(job, sources, now); err != nil {
		s.Audit.Append(model.AuditEvent{Actor: principal.ID, Action: "job.create", Resource: id, Outcome: outcome(err)})
		return model.Job{}, err
	}
	if err := s.Scheduler.Start(id, now); err != nil {
		s.Audit.Append(model.AuditEvent{Actor: principal.ID, Action: "job.create", Resource: id, Outcome: outcome(err)})
		return model.Job{}, err
	}
	if err := s.persist(now); err != nil {
		s.Audit.Append(model.AuditEvent{Actor: principal.ID, Action: "job.create", Resource: id, Outcome: outcome(err)})
		return model.Job{}, err
	}
	stored, _ := s.Scheduler.Job(id)
	s.Audit.Append(model.AuditEvent{Actor: principal.ID, Action: "job.create", Resource: id, Outcome: "accepted"})
	return stored, nil
}

func (s *Service) CancelJob(principal model.Principal, id string) error {
	now := time.Now()
	err := s.Scheduler.Cancel(id, now)
	if err == nil {
		err = s.persist(now)
	}
	s.Audit.Append(model.AuditEvent{Actor: principal.ID, Action: "job.cancel", Resource: id, Outcome: outcome(err)})
	return err
}

func (s *Service) RegisterWorker(worker model.WorkerSession) (model.WorkerSession, error) {
	now := time.Now()
	registered, err := s.Scheduler.RegisterWorker(worker, now)
	if err == nil {
		err = s.persist(now)
	}
	s.Audit.Append(model.AuditEvent{Actor: worker.WorkerID, Action: "worker.register", Resource: worker.SessionID, Outcome: outcome(err)})
	s.Metrics.Add("worker_registrations_total", map[string]string{"outcome": outcome(err)}, 1)
	if err != nil {
		return model.WorkerSession{}, err
	}
	return registered, nil
}

func (s *Service) Heartbeat(workerID, sessionID string) error {
	now := time.Now()
	err := s.Scheduler.Heartbeat(workerID, sessionID, now)
	if err == nil {
		err = s.persist(now)
	}
	s.Metrics.Add("worker_heartbeats_total", map[string]string{"outcome": outcome(err)}, 1)
	return err
}

func (s *Service) IssueLease(workerID, sessionID string) (model.Lease, error) {
	now := time.Now()
	s.Scheduler.Expire(now)
	lease, err := s.Scheduler.Issue(workerID, sessionID, now)
	if err == nil {
		err = s.persist(now)
	}
	s.Audit.Append(model.AuditEvent{Actor: workerID, Action: "lease.issue", Resource: lease.ShardID, Outcome: outcome(err)})
	s.Metrics.Add("leases_total", map[string]string{"outcome": outcome(err)}, 1)
	if err != nil {
		return model.Lease{}, err
	}
	return lease, nil
}

func (s *Service) RenewLease(lease model.Lease) (model.Lease, error) {
	now := time.Now()
	renewed, err := s.Scheduler.Renew(lease, now)
	if err == nil {
		err = s.persist(now)
	}
	s.Metrics.Add("lease_renewals_total", map[string]string{"outcome": outcome(err)}, 1)
	if err != nil {
		return model.Lease{}, err
	}
	return renewed, nil
}

func (s *Service) Ingest(lease model.Lease, batch model.ResultBatch) (ingest.BatchReceipt, bool, error) {
	now := time.Now()
	if err := s.Scheduler.Validate(lease, now); err != nil {
		return ingest.BatchReceipt{}, false, err
	}
	if batch.JobID != lease.JobID || batch.ShardID != lease.ShardID || batch.Generation != lease.Generation || batch.PolicyDigest != lease.PolicyDigest || batch.SessionID != lease.SessionID || batch.Attempt != lease.Attempt || batch.LeaseToken != lease.Token {
		return ingest.BatchReceipt{}, false, errors.New("batch authority mismatch")
	}
	digest, err := protocol.CanonicalBatchDigest(batch)
	if err != nil {
		return ingest.BatchReceipt{}, false, err
	}
	if batch.BodyDigest != digest {
		return ingest.BatchReceipt{}, false, errors.New("batch digest mismatch")
	}
	receipt, replay, err := s.Results.Accept(batch)
	if err != nil {
		s.Metrics.Add("result_batches_total", map[string]string{"outcome": "rejected"}, 1)
		return receipt, replay, err
	}
	if batch.Complete && !replay {
		if err = s.Scheduler.Commit(batch.ShardID, batch.NextCheckpoint, batch.Sequence, now); err != nil {
			s.Metrics.Add("result_batches_total", map[string]string{"outcome": "rejected"}, 1)
			return receipt, replay, err
		}
	}
	if err = s.persist(now); err != nil {
		s.Metrics.Add("result_batches_total", map[string]string{"outcome": "rejected"}, 1)
		return receipt, replay, err
	}
	s.Metrics.Add("result_batches_total", map[string]string{"outcome": "accepted"}, 1)
	return receipt, replay, nil
}

func (s *Service) Report(principal model.Principal, jobID string) (report.Report, error) {
	job, ok := s.Scheduler.Job(jobID)
	if !ok {
		return report.Report{}, errors.New("job not found")
	}
	authorizer := auth.New(s.Sources.List())
	visibleSources := authorizer.Sources(principal, "report")
	visibleFindings := authorizer.Findings(principal, "report", s.Results.Findings())
	return report.Aggregate(job, s.Scheduler.Shards(jobID), visibleSources, visibleFindings, s.Results.Errors(), s.Results.Truncations())
}

func (s *Service) PublishReport(principal model.Principal, jobID string) (report.Manifest, error) {
	value, err := s.Report(principal, jobID)
	if err != nil {
		return report.Manifest{}, err
	}
	manifest, err := s.Publisher.Publish(value)
	if err == nil {
		err = s.persist(time.Now())
	}
	s.Audit.Append(model.AuditEvent{Actor: principal.ID, Action: "report.publish", Resource: jobID, Outcome: outcome(err)})
	if err != nil {
		return report.Manifest{}, err
	}
	return manifest, nil
}

func (s *Service) Export(principal model.Principal, jobID, format string) ([]byte, error) {
	value, err := s.Report(principal, jobID)
	if err != nil {
		return nil, err
	}
	if format == "json" {
		return report.JSON(value)
	}
	if format == "csv" {
		return report.CSV(value)
	}
	return nil, errors.New("unsupported export format")
}

func (s *Service) Readiness() observe.Readiness {
	return observe.Evaluate(s.Recovered, s.Sources.List(), s.available, s.Scheduler.Workers(), s.Config.RequiredWorkers, time.Now())
}

func (s *Service) Status() map[string]any {
	events, droppedAudit := s.Audit.Snapshot()
	metrics, droppedMetrics := s.Metrics.Snapshot()
	return map[string]any{
		"readiness":             s.Readiness(),
		"workers":               s.Scheduler.Workers(),
		"policies":              s.Policies.List(),
		"sources":               s.Sources.List(),
		"audit_events":          events,
		"audit_dropped":         droppedAudit,
		"metrics":               metrics,
		"metric_series_dropped": droppedMetrics,
		"state_generation":      s.stateGeneration,
	}
}

func outcome(err error) string {
	if err != nil {
		return "rejected"
	}
	return "accepted"
}

func contains(items []string, value string) bool {
	for _, item := range items {
		if item == "*" || item == value {
			return true
		}
	}
	return false
}

func AdminPrincipal(tenant string) model.Principal {
	return model.Principal{
		ID:          "local-admin",
		Tenant:      tenant,
		Departments: []string{"*"},
		Regions:     []string{"*"},
		Sources:     []string{"*"},
		Actions:     []string{"*"},
	}
}

func NewID(prefix string) string {
	return fmt.Sprintf("%s-%d", prefix, time.Now().UTC().UnixNano())
}
