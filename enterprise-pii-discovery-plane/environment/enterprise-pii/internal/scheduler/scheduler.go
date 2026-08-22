package scheduler

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"sort"
	"sync"
	"time"

	"enterprise-pii/internal/model"
)

type Scheduler struct {
	mu sync.Mutex
	jobs map[string]*model.Job
	shards map[string]*model.Shard
	workers map[string]model.WorkerSession
	leases map[string]model.Lease
	leaseDuration time.Duration
}

func New(duration time.Duration) *Scheduler {
	return &Scheduler{jobs: map[string]*model.Job{}, shards: map[string]*model.Shard{}, workers: map[string]model.WorkerSession{}, leases: map[string]model.Lease{}, leaseDuration: duration}
}

func token() string { var raw [24]byte; _, _ = rand.Read(raw[:]); return hex.EncodeToString(raw[:]) }

func (s *Scheduler) CreateJob(job model.Job, sources []model.Source, now time.Time) ([]model.Shard, error) {
	s.mu.Lock(); defer s.mu.Unlock()
	if _, exists := s.jobs[job.ID]; exists { return nil, errors.New("job already exists") }
	if job.ID == "" || job.PolicyDigest == "" || job.CorpusDigest == "" || job.Generation == 0 { return nil, errors.New("job pins are incomplete") }
	job.State = model.JobPlanned
	job.CreatedAt = now.UTC()
	job.UpdatedAt = job.CreatedAt
	s.jobs[job.ID] = &job
	out := make([]model.Shard, 0, len(sources))
	for _, source := range sources {
		shard := model.Shard{ID: job.ID + ":" + source.ID, JobID: job.ID, SourceID: source.ID, Generation: job.Generation, State: model.ShardPending, Required: source.Required}
		s.shards[shard.ID] = &shard
		out = append(out, shard)
	}
	return out, nil
}

func (s *Scheduler) Start(jobID string, now time.Time) error {
	s.mu.Lock(); defer s.mu.Unlock()
	job, ok := s.jobs[jobID]
	if !ok { return errors.New("job not found") }
	if job.State != model.JobPlanned { return errors.New("job is not planned") }
	job.State = model.JobRunning
	job.UpdatedAt = now.UTC()
	return nil
}

func (s *Scheduler) Cancel(jobID string, now time.Time) error {
	s.mu.Lock(); defer s.mu.Unlock()
	job, ok := s.jobs[jobID]
	if !ok { return errors.New("job not found") }
	if job.State == model.JobComplete || job.State == model.JobCancelled || job.State == model.JobFailed { return errors.New("job is terminal") }
	when := now.UTC()
	job.State = model.JobCancelling
	job.CancelledAt = &when
	job.UpdatedAt = when
	for id, lease := range s.leases { if lease.JobID == jobID { delete(s.leases, id) } }
	job.State = model.JobCancelled
	return nil
}

func (s *Scheduler) RegisterWorker(worker model.WorkerSession, now time.Time) (model.WorkerSession, error) {
	s.mu.Lock(); defer s.mu.Unlock()
	if worker.WorkerID == "" || worker.SessionID == "" || worker.DetectorBundle == "" { return model.WorkerSession{}, errors.New("worker identity is incomplete") }
	worker.StartedAt = now.UTC()
	worker.HeartbeatAt = worker.StartedAt
	worker.ExpiresAt = now.Add(3 * s.leaseDuration).UTC()
	s.workers[worker.WorkerID] = worker
	return worker, nil
}

func (s *Scheduler) Heartbeat(workerID, sessionID string, now time.Time) error {
	s.mu.Lock(); defer s.mu.Unlock()
	worker, ok := s.workers[workerID]
	if !ok || worker.SessionID != sessionID { return errors.New("stale worker session") }
	worker.HeartbeatAt = now.UTC()
	worker.ExpiresAt = now.Add(3 * s.leaseDuration).UTC()
	s.workers[workerID] = worker
	return nil
}

func (s *Scheduler) Issue(workerID, sessionID string, now time.Time) (model.Lease, error) {
	s.mu.Lock(); defer s.mu.Unlock()
	worker, ok := s.workers[workerID]
	if !ok || worker.SessionID != sessionID || !worker.ExpiresAt.After(now) { return model.Lease{}, errors.New("worker session is not current") }
	ids := make([]string, 0, len(s.shards))
	for id := range s.shards { ids = append(ids, id) }
	sort.Strings(ids)
	for _, id := range ids {
		shard := s.shards[id]
		job := s.jobs[shard.JobID]
		if shard.State != model.ShardPending || job.State != model.JobRunning || worker.DetectorBundle != job.DetectorBundle { continue }
		shard.Attempt++
		shard.State = model.ShardLeased
		lease := model.Lease{Token: token(), Tenant: job.Tenant, JobID: job.ID, ShardID: shard.ID, Generation: job.Generation, PolicyDigest: job.PolicyDigest, WorkerID: workerID, SessionID: sessionID, Attempt: shard.Attempt, IssuedAt: now.UTC(), Deadline: now.Add(s.leaseDuration).UTC()}
		s.leases[shard.ID] = lease
		return lease, nil
	}
	return model.Lease{}, errors.New("no eligible shard")
}

func (s *Scheduler) Renew(candidate model.Lease, now time.Time) (model.Lease, error) {
	s.mu.Lock(); defer s.mu.Unlock()
	current, ok := s.leases[candidate.ShardID]
	if !ok || current.Token != candidate.Token || current.SessionID != candidate.SessionID || current.Attempt != candidate.Attempt { return model.Lease{}, errors.New("lease authority changed") }
	if !current.Deadline.After(now) { return model.Lease{}, errors.New("lease expired") }
	current.Deadline = now.Add(s.leaseDuration).UTC()
	s.leases[candidate.ShardID] = current
	return current, nil
}

func (s *Scheduler) Validate(candidate model.Lease, now time.Time) error {
	s.mu.Lock(); defer s.mu.Unlock()
	current, ok := s.leases[candidate.ShardID]
	if !ok { return errors.New("lease absent") }
	job := s.jobs[current.JobID]
	worker := s.workers[current.WorkerID]
	if job == nil || job.State != model.JobRunning { return errors.New("job does not accept results") }
	if current.Token != candidate.Token || current.Generation != candidate.Generation || current.PolicyDigest != candidate.PolicyDigest || current.SessionID != candidate.SessionID || current.Attempt != candidate.Attempt { return errors.New("lease fence mismatch") }
	if !current.Deadline.After(now) || worker.SessionID != current.SessionID || !worker.ExpiresAt.After(now) { return errors.New("authority expired") }
	return nil
}

func (s *Scheduler) Commit(shardID, checkpoint string, sequence uint64) error {
	s.mu.Lock(); defer s.mu.Unlock()
	shard, ok := s.shards[shardID]
	if !ok || shard.State != model.ShardLeased { return errors.New("shard is not leased") }
	shard.State = model.ShardCommitted
	shard.Checkpoint = checkpoint
	shard.CommittedSequence = sequence
	delete(s.leases, shardID)
	return nil
}

func (s *Scheduler) Expire(now time.Time) []string {
	s.mu.Lock(); defer s.mu.Unlock()
	var expired []string
	for id, lease := range s.leases {
		if lease.Deadline.After(now) { continue }
		delete(s.leases, id)
		if shard := s.shards[id]; shard != nil && shard.State == model.ShardLeased { shard.State = model.ShardPending; expired = append(expired, id) }
	}
	sort.Strings(expired)
	return expired
}

func (s *Scheduler) Job(id string) (model.Job, bool) { s.mu.Lock(); defer s.mu.Unlock(); v, ok := s.jobs[id]; if !ok { return model.Job{}, false }; return *v, true }
func (s *Scheduler) Shards(jobID string) []model.Shard { s.mu.Lock(); defer s.mu.Unlock(); var out []model.Shard; for _, v := range s.shards { if v.JobID == jobID { out = append(out, *v) } }; sort.Slice(out, func(i,j int) bool{return out[i].ID<out[j].ID}); return out }
func (s *Scheduler) Workers() []model.WorkerSession { s.mu.Lock(); defer s.mu.Unlock(); var out []model.WorkerSession; for _, v := range s.workers { out=append(out,v) }; sort.Slice(out,func(i,j int)bool{return out[i].WorkerID<out[j].WorkerID}); return out }
