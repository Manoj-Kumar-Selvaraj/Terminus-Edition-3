package core

import "time"

func contains(values []string, target string) bool {
    for _, value := range values {
        if value == target { return true }
    }
    return false
}

func TrustedSource(policy Policy, req Request) bool {
    return contains(policy.TrustedSources[req.Surface], req.Source)
}

func SeverityDenied(policy Policy, vulnerabilities []Vulnerability) bool {
    for _, vuln := range vulnerabilities {
        if contains(policy.DenySeverities, vuln.Severity) { return true }
    }
    return false
}

func ExceptionFor(db ExceptionDB, req Request, policyCode string, now time.Time) *Exception {
    for i := range db.Exceptions {
        candidate := &db.Exceptions[i]
        expires, err := parseRFC3339(candidate.ExpiresAt)
        if err != nil || !now.Before(expires) { continue }
        if candidate.Digest != req.Digest { continue }
        if !contains(candidate.Surfaces, req.Surface) { continue }
        if !contains(candidate.Environments, req.Environment) { continue }
        if !contains(candidate.PolicyCodes, policyCode) { continue }
        return candidate
    }
    return nil
}
