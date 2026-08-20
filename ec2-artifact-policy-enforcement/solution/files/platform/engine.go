package platform

import (
	"fmt"
	"strings"
	"time"
)

func decisionID(req Request, policy Policy, code string, now time.Time) string {
	return stableID(req.RequestID, req.Digest, policy.Version, code, now.UTC().Format(time.RFC3339))
}

func baseDecision(req Request, policy Policy, now time.Time, verdict, code, message string) Decision {
	return Decision{
		DecisionID:     decisionID(req, policy, code, now),
		RequestID:      req.RequestID,
		Decision:       verdict,
		Code:           code,
		Message:        message,
		PolicyVersion:  policy.Version,
		ArtifactDigest: req.Digest,
		EvaluatedAt:    now.UTC().Format(time.RFC3339),
	}
}

func finish(stateDir string, decision Decision) (Decision, error) {
	if err := AppendAudit(stateDir, decision); err != nil {
		return decision, err
	}
	if err := WriteLastDecision(stateDir, decision); err != nil {
		return decision, err
	}
	return decision, nil
}

func allowWithException(policy Policy, req Request, exception Exception, secret []byte, now time.Time, vulnerabilities []Vulnerability, dbRevision string, cacheHit bool) Decision {
	decision := baseDecision(req, policy, now, "ALLOW", "ALLOW_EXCEPTION", "artifact vulnerability is covered by an exact, current exception")
	decision.ExceptionID = exception.ID
	decision.ScanDBRevision = dbRevision
	decision.CacheHit = cacheHit
	decision.Vulnerabilities = vulnerabilities
	permit := SignPermit(req, policy, secret, now)
	decision.Permit = &permit
	return decision
}

func requestOperationallyValid(req Request) error {
	if strings.TrimSpace(req.RequestID) == "" {
		return fmt.Errorf("request id is required")
	}
	if strings.TrimSpace(req.InstanceID) == "" {
		return fmt.Errorf("instance identity is required")
	}
	if strings.TrimSpace(req.Surface) == "" {
		return fmt.Errorf("artifact surface is required")
	}
	if strings.TrimSpace(req.Manager) == "" {
		return fmt.Errorf("artifact manager is required")
	}
	if strings.TrimSpace(req.Name) == "" {
		return fmt.Errorf("artifact name is required")
	}
	return nil
}

func Evaluate(policy Policy, scans ScanDB, exceptions ExceptionDB, req Request, stateDir string, secret []byte, now time.Time) (Decision, error) {
	req = NormalizeRequest(req)
	_ = BuildIdentity(req)
	_ = ApplicableRules(req)
	if err := requestOperationallyValid(req); err != nil {
		return Decision{}, err
	}
	if len(secret) == 0 {
		return Decision{}, fmt.Errorf("permit secret is empty")
	}
	if err := EnsureStateLayout(stateDir); err != nil {
		return Decision{}, err
	}
	lock, err := AcquireStateHandle(stateDir)
	if err != nil {
		return Decision{}, err
	}
	defer lock.Close()
	if err := RecoverAuditLegacy(stateDir); err != nil {
		return Decision{}, err
	}

	if MissingRequiredDigest(policy, req) {
		return finish(stateDir, baseDecision(req, policy, now, "DENY", "DENY_MISSING_DIGEST", "immutable artifact digest is required"))
	}
	if !TrustedSource(policy, req) {
		return finish(stateDir, baseDecision(req, policy, now, "DENY", "DENY_UNTRUSTED_SOURCE", fmt.Sprintf("source %q is not trusted for %s", req.Source, req.Surface)))
	}

	key := CacheKey(req, policy)
	cached, hit, err := LoadCache(stateDir, key, now)
	if err != nil {
		return Decision{}, err
	}
	if hit && !CacheEntryMatches(policy, req, cached) {
		hit = false
	}

	var vulnerabilities []Vulnerability
	var dbRevision string
	if hit {
		vulnerabilities = cached.Vulnerabilities
		dbRevision = cached.ScanDBRevision
	} else {
		scanned := Scan(scans, req.Digest)
		if !ScannerHealthy(scanned) {
			decision := baseDecision(req, policy, now, "DENY", "DENY_SCANNER_UNAVAILABLE", "current vulnerability evidence is unavailable")
			decision.ScanDBRevision = scanned.DBRevision
			return finish(stateDir, decision)
		}
		if !ScannerRevisionMatches(policy, scanned) {
			decision := baseDecision(req, policy, now, "DENY", "DENY_SCANNER_EVIDENCE_STALE", "scanner evidence does not match the policy scanner DB revision")
			decision.ScanDBRevision = scanned.DBRevision
			return finish(stateDir, decision)
		}
		vulnerabilities = scanned.Vulnerabilities
		dbRevision = scanned.DBRevision
		entry := CacheEntry{
			ArtifactDigest:  req.Digest,
			PolicyVersion:   policy.Version,
			ScanDBRevision:  dbRevision,
			Vulnerabilities: vulnerabilities,
			ScannedAt:       now.UTC().Format(time.RFC3339),
			ExpiresAt:       now.Add(time.Duration(policy.CacheTTLSeconds) * time.Second).UTC().Format(time.RFC3339),
		}
		if err := SaveCache(stateDir, key, entry); err != nil {
			return Decision{}, err
		}
	}

	if SeverityDenied(policy, vulnerabilities) {
		if exception := ExceptionFor(exceptions, req, "VULNERABILITY_THRESHOLD", now); exception != nil {
			return finish(stateDir, allowWithException(policy, req, *exception, secret, now, vulnerabilities, dbRevision, hit))
		}
		decision := baseDecision(req, policy, now, "DENY", "DENY_VULNERABLE", "artifact exceeds vulnerability severity policy")
		decision.ScanDBRevision = dbRevision
		decision.CacheHit = hit
		decision.Vulnerabilities = vulnerabilities
		return finish(stateDir, decision)
	}

	decision := baseDecision(req, policy, now, "ALLOW", "ALLOW_CLEAN", "artifact satisfies current software policy")
	decision.ScanDBRevision = dbRevision
	decision.CacheHit = hit
	decision.Vulnerabilities = vulnerabilities
	permit := SignPermit(req, policy, secret, now)
	decision.Permit = &permit
	return finish(stateDir, decision)
}
