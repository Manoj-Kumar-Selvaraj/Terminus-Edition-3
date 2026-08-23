package persistence

import (
	"encoding/json"
	"errors"
	"sort"
	"time"

	"enterprise-pii/internal/ingest"
	"enterprise-pii/internal/model"
)

type Snapshot struct {
	Schema              string                `json:"schema"`
	Generation          uint64                `json:"generation"`
	SavedAt             time.Time             `json:"saved_at"`
	Sources             []model.Source        `json:"sources"`
	Policies            []model.Policy        `json:"policies"`
	Jobs                []model.Job           `json:"jobs"`
	Shards              []model.Shard         `json:"shards"`
	Workers             []model.WorkerSession `json:"workers"`
	Leases              []model.Lease         `json:"leases"`
	Receipts            []ingest.BatchReceipt `json:"receipts"`
	Findings            []model.Finding       `json:"findings"`
	Errors              []model.ScanError     `json:"errors"`
	Truncations         []model.Truncation    `json:"truncations"`
	Checkpoints         map[string]string     `json:"checkpoints"`
	ReportGenerations   map[string][]uint64   `json:"report_generations"`
	RetentionLeases     []RetentionLease      `json:"retention_leases"`
	Audit               []model.AuditEvent    `json:"audit"`
	AuditDropped        uint64                `json:"audit_dropped"`
	MetricSeries        map[string]float64    `json:"metric_series"`
	MetricSeriesDropped uint64                `json:"metric_series_dropped"`
}

func EncodeSnapshot(snapshot Snapshot) ([]byte, error) {
	if err := ValidateSnapshot(snapshot); err != nil {
		return nil, err
	}
	normalizeSnapshot(&snapshot)
	return json.Marshal(snapshot)
}

func DecodeSnapshot(body []byte) (Snapshot, error) {
	var snapshot Snapshot
	decoder := json.NewDecoder(bytesReader(body))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&snapshot); err != nil {
		return Snapshot{}, errors.New("invalid state snapshot")
	}
	if err := ValidateSnapshot(snapshot); err != nil {
		return Snapshot{}, err
	}
	normalizeSnapshot(&snapshot)
	return snapshot, nil
}

func ValidateSnapshot(snapshot Snapshot) error {
	if snapshot.Schema != "enterprise-pii-state/v1" {
		return errors.New("unsupported state snapshot schema")
	}
	if snapshot.Generation == 0 {
		return errors.New("state generation must be positive")
	}
	if snapshot.SavedAt.IsZero() {
		return errors.New("state snapshot timestamp missing")
	}

	sourceIDs := map[string]bool{}
	for _, source := range snapshot.Sources {
		if source.ID == "" || source.CanonicalRoot == "" || source.Department == "" || source.Region == "" {
			return errors.New("source identity incomplete")
		}
		if sourceIDs[source.ID] {
			return errors.New("duplicate source identity")
		}
		sourceIDs[source.ID] = true
	}

	policyDigests := map[string]string{}
	for _, policy := range snapshot.Policies {
		if policy.Version == "" || policy.Digest == "" {
			return errors.New("policy pin incomplete")
		}
		if prior, ok := policyDigests[policy.Version]; ok && prior != policy.Digest {
			return errors.New("policy version conflict")
		}
		policyDigests[policy.Version] = policy.Digest
	}

	jobs := map[string]model.Job{}
	for _, job := range snapshot.Jobs {
		if job.ID == "" || job.Generation == 0 || job.Tenant == "" {
			return errors.New("job identity incomplete")
		}
		if digest, ok := policyDigests[job.PolicyVersion]; !ok || digest != job.PolicyDigest {
			return errors.New("job policy fence is unresolved")
		}
		if _, exists := jobs[job.ID]; exists {
			return errors.New("duplicate job identity")
		}
		jobs[job.ID] = job
	}

	shards := map[string]model.Shard{}
	shardsByJob := map[string][]model.Shard{}
	for _, shard := range snapshot.Shards {
		job, ok := jobs[shard.JobID]
		if !ok || job.Generation != shard.Generation {
			return errors.New("shard generation fence is unresolved")
		}
		if _, exists := shards[shard.ID]; exists {
			return errors.New("duplicate shard identity")
		}
		if !sourceIDs[shard.SourceID] {
			return errors.New("shard source fence is unresolved")
		}
		shards[shard.ID] = shard
		shardsByJob[shard.JobID] = append(shardsByJob[shard.JobID], shard)
	}

	sessions := map[string]model.WorkerSession{}
	for _, worker := range snapshot.Workers {
		if worker.WorkerID == "" || worker.SessionID == "" || worker.DetectorBundle == "" {
			return errors.New("worker session incomplete")
		}
		key := worker.WorkerID + "\x1f" + worker.SessionID
		if _, exists := sessions[key]; exists {
			return errors.New("duplicate worker session")
		}
		sessions[key] = worker
	}

	for _, lease := range snapshot.Leases {
		shard, ok := shards[lease.ShardID]
		if !ok || shard.JobID != lease.JobID || shard.Generation != lease.Generation || shard.Attempt != lease.Attempt {
			return errors.New("lease shard fence is unresolved")
		}
		worker, ok := sessions[lease.WorkerID+"\x1f"+lease.SessionID]
		if !ok {
			return errors.New("lease session fence is unresolved")
		}
		job := jobs[lease.JobID]
		if job.PolicyDigest != lease.PolicyDigest || job.Tenant != lease.Tenant {
			return errors.New("lease policy fence is unresolved")
		}
		if job.State != model.JobRunning {
			return errors.New("lease job fence is unresolved")
		}
		if shard.State != model.ShardLeased && shard.State != model.ShardCommitting {
			return errors.New("lease shard state is unresolved")
		}
		if !lease.Deadline.After(snapshot.SavedAt) || !worker.ExpiresAt.After(snapshot.SavedAt) {
			return errors.New("lease authority expired in snapshot")
		}
	}

	batchIDs := map[string]string{}
	for _, receipt := range snapshot.Receipts {
		if receipt.BatchID == "" || receipt.Digest == "" {
			return errors.New("batch receipt incomplete")
		}
		if prior, ok := batchIDs[receipt.BatchID]; ok && prior != receipt.Digest {
			return errors.New("batch identity conflict in snapshot")
		}
		batchIDs[receipt.BatchID] = receipt.Digest
	}

	findingIDs := map[string]bool{}
	locationKeys := map[string]bool{}
	for _, finding := range snapshot.Findings {
		if finding.ID == "" || finding.Fingerprint == "" || finding.MaskedEvidence == "" || finding.Category == "" {
			return errors.New("finding privacy envelope incomplete")
		}
		if finding.Location.SourceID == "" || finding.Location.RecordID == "" {
			return errors.New("finding location incomplete")
		}
		if !sourceIDs[finding.Location.SourceID] {
			return errors.New("finding source fence is unresolved")
		}
		if finding.PolicyVersion != "" {
			if digest, ok := policyDigests[finding.PolicyVersion]; !ok || digest != finding.PolicyDigest {
				return errors.New("finding policy fence is unresolved")
			}
		}
		if findingIDs[finding.ID] {
			return errors.New("duplicate finding identity")
		}
		findingIDs[finding.ID] = true
		key := finding.Location.SourceID + "\x1f" + finding.Location.CanonicalPath + "\x1f" + finding.Location.ArchiveMember + "\x1f" + finding.Location.RecordID + "\x1f" + finding.Location.FieldPath
		if locationKeys[key+finding.Fingerprint] {
			return errors.New("duplicate governed finding location")
		}
		locationKeys[key+finding.Fingerprint] = true
	}

	for _, receipt := range snapshot.Receipts {
		for _, findingID := range receipt.FindingIDs {
			if !findingIDs[findingID] {
				return errors.New("receipt finding fence is unresolved")
			}
		}
	}

	for _, scanError := range snapshot.Errors {
		if scanError.Kind == "" || scanError.SourceID == "" || scanError.Detail == "" {
			return errors.New("scan error incomplete")
		}
		if !sourceIDs[scanError.SourceID] {
			return errors.New("scan error source fence is unresolved")
		}
	}

	for _, truncation := range snapshot.Truncations {
		if truncation.Budget == "" || truncation.SourceID == "" || truncation.Limit <= 0 {
			return errors.New("truncation incomplete")
		}
		if !sourceIDs[truncation.SourceID] {
			return errors.New("truncation source fence is unresolved")
		}
	}

	for shardID, checkpoint := range snapshot.Checkpoints {
		shard, ok := shards[shardID]
		if !ok {
			return errors.New("checkpoint shard fence is unresolved")
		}
		if shard.Checkpoint != "" && shard.Checkpoint != checkpoint {
			return errors.New("checkpoint value conflict")
		}
	}

	for jobID, generations := range snapshot.ReportGenerations {
		if _, ok := jobs[jobID]; !ok {
			return errors.New("report generation job fence is unresolved")
		}
		for _, generation := range generations {
			if generation == 0 {
				return errors.New("report generation must be positive")
			}
		}
	}

	for _, lease := range snapshot.RetentionLeases {
		if lease.ID == "" || len(lease.Generations) == 0 || lease.Reason == "" {
			return errors.New("retention lease incomplete")
		}
	}

	if len(snapshot.Audit) > 0 {
		if snapshot.Audit[0].Sequence == 0 {
			return errors.New("audit sequence must be positive")
		}
		for index := 1; index < len(snapshot.Audit); index++ {
			if snapshot.Audit[index].Sequence <= snapshot.Audit[index-1].Sequence {
				return errors.New("audit sequence is not monotonic")
			}
		}
	}

	for key := range snapshot.MetricSeries {
		if key == "" {
			return errors.New("metric series key incomplete")
		}
	}

	for _, job := range snapshot.Jobs {
		jobShards := shardsByJob[job.ID]
		switch job.State {
		case model.JobComplete:
			for _, shard := range jobShards {
				if shard.Required && !shardTerminal(shard.State) {
					return errors.New("complete job has unresolved required shard")
				}
			}
		case model.JobRunning:
			for _, lease := range snapshot.Leases {
				if lease.JobID == job.ID && !lease.Deadline.After(snapshot.SavedAt) {
					return errors.New("running job retains expired lease")
				}
			}
		case model.JobCancelled:
			for _, shard := range jobShards {
				if shard.State == model.ShardLeased || shard.State == model.ShardCommitting {
					return errors.New("cancelled job retains active shard lease")
				}
			}
		}
	}

	return nil
}

func shardTerminal(state model.ShardState) bool {
	return state == model.ShardCommitted || state == model.ShardSkipped || state == model.ShardFailed
}

func ReferencedGenerations(snapshot Snapshot, now time.Time) map[uint64]bool {
	referenced := map[uint64]bool{snapshot.Generation: true}
	for _, job := range snapshot.Jobs {
		if job.State != model.JobComplete && job.State != model.JobCancelled && job.State != model.JobFailed {
			referenced[job.Generation] = true
		}
	}
	for _, lease := range snapshot.RetentionLeases {
		if lease.ExpiresAt.After(now) {
			for _, generation := range lease.Generations {
				referenced[generation] = true
			}
		}
	}
	for _, generations := range snapshot.ReportGenerations {
		for _, generation := range generations {
			referenced[generation] = true
		}
	}
	return referenced
}

func normalizeSnapshot(snapshot *Snapshot) {
	sort.Slice(snapshot.Sources, func(i, j int) bool { return snapshot.Sources[i].ID < snapshot.Sources[j].ID })
	sort.Slice(snapshot.Policies, func(i, j int) bool { return snapshot.Policies[i].Version < snapshot.Policies[j].Version })
	sort.Slice(snapshot.Jobs, func(i, j int) bool { return snapshot.Jobs[i].ID < snapshot.Jobs[j].ID })
	sort.Slice(snapshot.Shards, func(i, j int) bool { return snapshot.Shards[i].ID < snapshot.Shards[j].ID })
	sort.Slice(snapshot.Workers, func(i, j int) bool { return snapshot.Workers[i].WorkerID < snapshot.Workers[j].WorkerID })
	sort.Slice(snapshot.Leases, func(i, j int) bool { return snapshot.Leases[i].ShardID < snapshot.Leases[j].ShardID })
	sort.Slice(snapshot.Receipts, func(i, j int) bool { return snapshot.Receipts[i].BatchID < snapshot.Receipts[j].BatchID })
	sort.Slice(snapshot.Findings, func(i, j int) bool { return snapshot.Findings[i].ID < snapshot.Findings[j].ID })
	sort.Slice(snapshot.Audit, func(i, j int) bool { return snapshot.Audit[i].Sequence < snapshot.Audit[j].Sequence })
}

type sliceReader struct {
	body   []byte
	offset int
}

func bytesReader(body []byte) *sliceReader { return &sliceReader{body: body} }

func (r *sliceReader) Read(target []byte) (int, error) {
	if r.offset >= len(r.body) {
		return 0, errors.New("EOF")
	}
	count := copy(target, r.body[r.offset:])
	r.offset += count
	return count, nil
}
