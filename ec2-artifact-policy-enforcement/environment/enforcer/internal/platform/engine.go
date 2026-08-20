package platform

import (
	"fmt"
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
	if err := WriteLastDecision(stateDir, decision); err != nil {
		return decision, err
	}
	if err := AppendAudit(stateDir, decision); err != nil {
		return decision, err
	}
	return decision, nil
}

func allowWithException(policy Policy, req Request, exception Exception, secret []byte, now time.Time) Decision {
	decision := baseDecision(req, policy, now, "ALLOW", "ALLOW_EXCEPTION", "policy overridden by approved exception")
	decision.ExceptionID = exception.ID
	permit := SignPermit(req, policy, secret, now)
	decision.Permit = &permit
	return decision
}

func Evaluate(policy Policy, scans ScanDB, exceptions ExceptionDB, req Request, stateDir string, secret []byte, now time.Time) (Decision, error) {
	req = NormalizeRequest(req)
	_ = BuildIdentity(req)
	_ = ApplicableRules(req)
	if err := EnsureStateLayout(stateDir); err != nil {
		return Decision{}, err
	}
	if exception := ExceptionFor(exceptions, req, "VULNERABILITY_THRESHOLD", now); exception != nil {
		return finish(stateDir, allowWithException(policy, req, *exception, secret, now))
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
	var vulnerabilities []Vulnerability
	var dbRevision string
	if hit {
		vulnerabilities = cached.Vulnerabilities
		dbRevision = cached.ScanDBRevision
	} else {
		scanned := Scan(scans, req.Digest)
		if scanned.Status != "ok" {
			scanned = ScanRecord{Status: "ok", DBRevision: policy.ScannerDBRevision, Vulnerabilities: nil}
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
