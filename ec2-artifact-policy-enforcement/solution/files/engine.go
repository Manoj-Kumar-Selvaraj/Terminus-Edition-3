package core

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "fmt"
    "time"
)

func decisionID(req Request, policy Policy, code string, now time.Time) string {
    sum := sha256.Sum256([]byte(req.RequestID + "|" + req.Digest + "|" + policy.Version + "|" + code + "|" + now.UTC().Format(time.RFC3339)))
    return hex.EncodeToString(sum[:])
}

func finish(stateDir string, decision Decision) (Decision, error) {
    if err := AppendAudit(stateDir, decision); err != nil { return decision, err }
    if err := WriteLastDecision(stateDir, decision); err != nil { return decision, err }
    return decision, nil
}

func baseDecision(req Request, policy Policy, now time.Time, verdict, code, message string) Decision {
    return Decision{DecisionID: decisionID(req, policy, code, now), RequestID: req.RequestID, Decision: verdict, Code: code, Message: message, PolicyVersion: policy.Version, ArtifactDigest: req.Digest, EvaluatedAt: now.UTC().Format(time.RFC3339)}
}

func permitPayload(permit Permit) string {
    return permit.RequestID + "|" + permit.InstanceID + "|" + permit.ArtifactDigest + "|" + permit.PolicyVersion + "|" + permit.ExpiresAt
}

func SignPermit(req Request, policy Policy, secret []byte, now time.Time) Permit {
    permit := Permit{RequestID: req.RequestID, InstanceID: req.InstanceID, ArtifactDigest: req.Digest, PolicyVersion: policy.Version, ExpiresAt: now.Add(time.Duration(policy.PermitTTLSeconds) * time.Second).UTC().Format(time.RFC3339)}
    mac := hmac.New(sha256.New, secret)
    _, _ = mac.Write([]byte(permitPayload(permit)))
    permit.Signature = hex.EncodeToString(mac.Sum(nil))
    return permit
}

func VerifyPermit(permit Permit, req Request, policy Policy, secret []byte, now time.Time) (bool, string) {
    expires, err := parseRFC3339(permit.ExpiresAt)
    if err != nil || !now.Before(expires) { return false, "PERMIT_EXPIRED" }
    if permit.RequestID != req.RequestID || permit.InstanceID != req.InstanceID || permit.ArtifactDigest != req.Digest || permit.PolicyVersion != policy.Version { return false, "PERMIT_SCOPE_MISMATCH" }
    mac := hmac.New(sha256.New, secret)
    _, _ = mac.Write([]byte(permitPayload(permit)))
    expected := mac.Sum(nil)
    supplied, err := hex.DecodeString(permit.Signature)
    if err != nil || !hmac.Equal(supplied, expected) { return false, "PERMIT_SIGNATURE_INVALID" }
    return true, "PERMIT_VALID"
}

func Evaluate(policy Policy, scans ScanDB, exceptions ExceptionDB, req Request, stateDir string, secret []byte, now time.Time) (Decision, error) {
    if req.Surface != "package" && req.Surface != "container" && req.Surface != "dependency" {
        return finish(stateDir, baseDecision(req, policy, now, "DENY", "DENY_UNTRUSTED_SOURCE", "unsupported acquisition surface"))
    }
    if policy.RequireDigest[req.Surface] && req.Digest == "" {
        return finish(stateDir, baseDecision(req, policy, now, "DENY", "DENY_MISSING_DIGEST", "immutable artifact digest is required"))
    }
    if !TrustedSource(policy, req) {
        return finish(stateDir, baseDecision(req, policy, now, "DENY", "DENY_UNTRUSTED_SOURCE", fmt.Sprintf("source %q is not trusted for %s", req.Source, req.Surface)))
    }
    key := CacheKey(req, policy)
    cached, hit, err := LoadCache(stateDir, key, now)
    if err != nil { return Decision{}, err }
    var vulnerabilities []Vulnerability
    var dbRevision string
    if hit {
        if cached.ArtifactDigest != req.Digest || cached.PolicyVersion != policy.Version || cached.ScanDBRevision != policy.ScannerDBRevision {
            hit = false
        } else {
            vulnerabilities = cached.Vulnerabilities
            dbRevision = cached.ScanDBRevision
        }
    }
    if !hit {
        scanned := Scan(scans, req.Digest)
        if scanned.Status != "ok" {
            return finish(stateDir, baseDecision(req, policy, now, "DENY", "DENY_SCANNER_UNAVAILABLE", "current vulnerability evidence is unavailable"))
        }
        if scanned.DBRevision != policy.ScannerDBRevision {
            decision := baseDecision(req, policy, now, "DENY", "DENY_SCANNER_EVIDENCE_STALE", "scanner evidence revision does not match active policy")
            decision.ScanDBRevision = scanned.DBRevision
            return finish(stateDir, decision)
        }
        vulnerabilities = scanned.Vulnerabilities
        dbRevision = scanned.DBRevision
        entry := CacheEntry{ArtifactDigest: req.Digest, PolicyVersion: policy.Version, ScanDBRevision: dbRevision, Vulnerabilities: vulnerabilities, ScannedAt: now.UTC().Format(time.RFC3339), ExpiresAt: now.Add(time.Duration(policy.CacheTTLSeconds) * time.Second).UTC().Format(time.RFC3339)}
        if err := SaveCache(stateDir, key, entry); err != nil { return Decision{}, err }
    }
    if SeverityDenied(policy, vulnerabilities) {
        if exception := ExceptionFor(exceptions, req, "VULNERABILITY_THRESHOLD", now); exception != nil {
            decision := baseDecision(req, policy, now, "ALLOW", "ALLOW_EXCEPTION", "vulnerability policy overridden by approved exception")
            decision.ExceptionID = exception.ID; decision.ScanDBRevision = dbRevision; decision.CacheHit = hit; decision.Vulnerabilities = vulnerabilities
            permit := SignPermit(req, policy, secret, now); decision.Permit = &permit
            return finish(stateDir, decision)
        }
        decision := baseDecision(req, policy, now, "DENY", "DENY_VULNERABLE", "artifact exceeds vulnerability severity policy")
        decision.ScanDBRevision = dbRevision; decision.CacheHit = hit; decision.Vulnerabilities = vulnerabilities
        return finish(stateDir, decision)
    }
    decision := baseDecision(req, policy, now, "ALLOW", "ALLOW_CLEAN", "artifact satisfies current software policy")
    decision.ScanDBRevision = dbRevision; decision.CacheHit = hit; decision.Vulnerabilities = vulnerabilities
    permit := SignPermit(req, policy, secret, now); decision.Permit = &permit
    return finish(stateDir, decision)
}
