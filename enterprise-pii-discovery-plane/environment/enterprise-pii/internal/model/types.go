package model

import "time"

type JobState string
type ShardState string

const (
	JobPlanned JobState = "PLANNED"
	JobRunning JobState = "RUNNING"
	JobFinalizing JobState = "FINALIZING"
	JobComplete JobState = "COMPLETE"
	JobCancelling JobState = "CANCELLING"
	JobCancelled JobState = "CANCELLED"
	JobFailed JobState = "FAILED"
	ShardPending ShardState = "PENDING"
	ShardLeased ShardState = "LEASED"
	ShardCommitting ShardState = "COMMITTING"
	ShardCommitted ShardState = "COMMITTED"
	ShardSkipped ShardState = "SKIPPED"
	ShardFailed ShardState = "FAILED"
)

type Source struct {
	ID string `json:"id"`
	Root string `json:"root"`
	CanonicalRoot string `json:"canonical_root"`
	Department string `json:"department"`
	Region string `json:"region"`
	Owner string `json:"owner"`
	Required bool `json:"required"`
	Generation string `json:"generation"`
}

type Budget struct {
	MaxFileBytes int64 `json:"max_file_bytes"`
	MaxRecordsPerFile int `json:"max_records_per_file"`
	MaxNesting int `json:"max_nesting"`
	MaxArchiveEntries int `json:"max_archive_entries"`
	MaxArchiveBytes int64 `json:"max_archive_bytes"`
	MaxMatchesPerRecord int `json:"max_matches_per_record"`
	MaxErrorsPerSource int `json:"max_errors_per_source"`
	MaxScanSeconds int `json:"max_scan_seconds"`
}

type ScopeRule struct {
	ID string `json:"id"`
	Tenant string `json:"tenant"`
	Category string `json:"category"`
	Department string `json:"department,omitempty"`
	Region string `json:"region,omitempty"`
	SourceID string `json:"source_id,omitempty"`
	Fingerprint string `json:"fingerprint,omitempty"`
	Reason string `json:"reason"`
	ExpiresAt *time.Time `json:"expires_at,omitempty"`
}

type Policy struct {
	Version string `json:"version"`
	Digest string `json:"digest"`
	KeyEpoch string `json:"key_epoch"`
	DetectorBundle string `json:"detector_bundle"`
	MinimumConfidence float64 `json:"minimum_confidence"`
	Categories []string `json:"categories"`
	Budgets Budget `json:"budgets"`
	Allowlist []ScopeRule `json:"allowlist"`
	Suppressions []ScopeRule `json:"suppressions"`
	PublishedAt time.Time `json:"published_at"`
}

type Job struct {
	ID string `json:"id"`
	Tenant string `json:"tenant"`
	Generation uint64 `json:"generation"`
	State JobState `json:"state"`
	PolicyVersion string `json:"policy_version"`
	PolicyDigest string `json:"policy_digest"`
	DetectorBundle string `json:"detector_bundle"`
	CorpusDigest string `json:"corpus_digest"`
	SourceGeneration string `json:"source_generation"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	CancelledAt *time.Time `json:"cancelled_at,omitempty"`
}

type Shard struct {
	ID string `json:"id"`
	JobID string `json:"job_id"`
	SourceID string `json:"source_id"`
	Generation uint64 `json:"generation"`
	State ShardState `json:"state"`
	Attempt uint32 `json:"attempt"`
	Required bool `json:"required"`
	Checkpoint string `json:"checkpoint,omitempty"`
	CommittedSequence uint64 `json:"committed_sequence"`
	ErrorCode string `json:"error_code,omitempty"`
}

type WorkerSession struct {
	WorkerID string `json:"worker_id"`
	SessionID string `json:"session_id"`
	DetectorBundle string `json:"detector_bundle"`
	Formats []string `json:"formats"`
	StartedAt time.Time `json:"started_at"`
	HeartbeatAt time.Time `json:"heartbeat_at"`
	ExpiresAt time.Time `json:"expires_at"`
}

type Lease struct {
	Token string `json:"token"`
	Tenant string `json:"tenant"`
	JobID string `json:"job_id"`
	ShardID string `json:"shard_id"`
	Generation uint64 `json:"generation"`
	PolicyDigest string `json:"policy_digest"`
	WorkerID string `json:"worker_id"`
	SessionID string `json:"session_id"`
	Attempt uint32 `json:"attempt"`
	IssuedAt time.Time `json:"issued_at"`
	Deadline time.Time `json:"deadline"`
}

type Location struct {
	SourceID string `json:"source_id"`
	CanonicalPath string `json:"canonical_path"`
	ArchiveMember string `json:"archive_member,omitempty"`
	RecordID string `json:"record_id"`
	FieldPath string `json:"field_path"`
	Line int64 `json:"line"`
	ByteStart int64 `json:"byte_start"`
	ByteEnd int64 `json:"byte_end"`
}

type Finding struct {
	ID string `json:"id"`
	Category string `json:"category"`
	MaskedEvidence string `json:"masked_evidence"`
	Fingerprint string `json:"fingerprint"`
	Confidence float64 `json:"confidence"`
	DetectorRevision string `json:"detector_revision"`
	PolicyVersion string `json:"policy_version"`
	PolicyDigest string `json:"policy_digest"`
	Location Location `json:"location"`
	Lineage []string `json:"lineage"`
	Suppressed bool `json:"suppressed"`
}

type ScanError struct {
	Kind string `json:"kind"`
	SourceID string `json:"source_id"`
	RecordID string `json:"record_id,omitempty"`
	FieldPath string `json:"field_path,omitempty"`
	Detail string `json:"detail"`
	Recoverable bool `json:"recoverable"`
}

type Truncation struct {
	Budget string `json:"budget"`
	SourceID string `json:"source_id"`
	Limit int64 `json:"limit"`
	Observed int64 `json:"observed"`
	Checkpoint string `json:"checkpoint,omitempty"`
}

type ResultBatch struct {
	ID string `json:"id"`
	BodyDigest string `json:"body_digest"`
	JobID string `json:"job_id"`
	ShardID string `json:"shard_id"`
	Generation uint64 `json:"generation"`
	PolicyDigest string `json:"policy_digest"`
	SessionID string `json:"session_id"`
	Attempt uint32 `json:"attempt"`
	LeaseToken string `json:"lease_token"`
	Sequence uint64 `json:"sequence"`
	PreviousCheckpoint string `json:"previous_checkpoint"`
	NextCheckpoint string `json:"next_checkpoint"`
	Findings []Finding `json:"findings"`
	Errors []ScanError `json:"errors"`
	Truncations []Truncation `json:"truncations"`
	Complete bool `json:"complete"`
}

type Principal struct {
	ID string `json:"id"`
	Tenant string `json:"tenant"`
	Departments []string `json:"departments"`
	Regions []string `json:"regions"`
	Sources []string `json:"sources"`
	Actions []string `json:"actions"`
}

type AuditEvent struct {
	Sequence uint64 `json:"sequence"`
	At time.Time `json:"at"`
	Actor string `json:"actor"`
	Action string `json:"action"`
	Resource string `json:"resource"`
	Outcome string `json:"outcome"`
	Detail map[string]string `json:"detail,omitempty"`
}