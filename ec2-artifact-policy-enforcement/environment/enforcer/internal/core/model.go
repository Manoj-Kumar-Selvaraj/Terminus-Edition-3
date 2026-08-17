package core

import "time"

type Policy struct {
    Version           string              `json:"version"`
    ScannerDBRevision string              `json:"scanner_db_revision"`
    DenySeverities    []string            `json:"deny_severities"`
    TrustedSources    map[string][]string `json:"trusted_sources"`
    RequireDigest     map[string]bool     `json:"require_digest"`
    CacheTTLSeconds   int64               `json:"cache_ttl_seconds"`
    PermitTTLSeconds  int64               `json:"permit_ttl_seconds"`
}

type Request struct {
    RequestID   string `json:"request_id"`
    InstanceID  string `json:"instance_id"`
    Environment string `json:"environment"`
    Surface     string `json:"surface"`
    Manager     string `json:"manager"`
    Name        string `json:"name"`
    Version     string `json:"version"`
    Source      string `json:"source"`
    Digest      string `json:"digest"`
    Action      string `json:"action"`
}

type Vulnerability struct {
    ID       string `json:"id"`
    Severity string `json:"severity"`
}

type ScanRecord struct {
    Status          string          `json:"status"`
    DBRevision      string          `json:"db_revision"`
    Vulnerabilities []Vulnerability `json:"vulnerabilities"`
}

type ScanDB struct { Records map[string]ScanRecord `json:"records"` }

type Exception struct {
    ID           string   `json:"id"`
    Digest       string   `json:"digest"`
    Surfaces     []string `json:"surfaces"`
    Environments []string `json:"environments"`
    PolicyCodes  []string `json:"policy_codes"`
    ExpiresAt    string   `json:"expires_at"`
}

type ExceptionDB struct { Exceptions []Exception `json:"exceptions"` }

type Permit struct {
    RequestID      string `json:"request_id"`
    InstanceID     string `json:"instance_id"`
    ArtifactDigest string `json:"artifact_digest"`
    PolicyVersion  string `json:"policy_version"`
    ExpiresAt      string `json:"expires_at"`
    Signature      string `json:"signature"`
}

type Decision struct {
    DecisionID       string          `json:"decision_id"`
    RequestID        string          `json:"request_id"`
    Decision         string          `json:"decision"`
    Code             string          `json:"code"`
    Message          string          `json:"message"`
    PolicyVersion    string          `json:"policy_version"`
    ArtifactDigest   string          `json:"artifact_digest"`
    ScanDBRevision   string          `json:"scan_db_revision,omitempty"`
    ExceptionID      string          `json:"exception_id,omitempty"`
    CacheHit         bool            `json:"cache_hit"`
    EvaluatedAt      string          `json:"evaluated_at"`
    Vulnerabilities []Vulnerability `json:"vulnerabilities,omitempty"`
    Permit           *Permit         `json:"permit,omitempty"`
}

type CacheEntry struct {
    ArtifactDigest   string          `json:"artifact_digest"`
    PolicyVersion    string          `json:"policy_version"`
    ScanDBRevision   string          `json:"scan_db_revision"`
    Vulnerabilities []Vulnerability `json:"vulnerabilities"`
    ScannedAt        string          `json:"scanned_at"`
    ExpiresAt        string          `json:"expires_at"`
}

func parseRFC3339(value string) (time.Time, error) { return time.Parse(time.RFC3339, value) }
