#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "ec2-artifact-policy-enforcement"
ENV_PLATFORM = TASK / "environment" / "enforcer" / "internal" / "platform"
SOL = TASK / "solution"
SOL_PLATFORM = SOL / "files" / "platform"


def replace_function(text: str, start: str, next_start: str, replacement: str) -> str:
    begin = text.index(start)
    end = text.index(next_start, begin)
    return text[:begin] + replacement.rstrip() + "\n\n" + text[end:]


def materialize_evidence_runtime() -> None:
    text = (ENV_PLATFORM / "evidence_runtime.go").read_text()
    text = text.replace(
        "\tassessment.Usable = present\n",
        "\tassessment.Usable = strictUsable\n",
        1,
    )
    text = replace_function(
        text,
        "func legacyScannerRecord",
        "func cacheEntryFromScanner",
        '''func legacyScannerRecord(context *EvaluationContext, assessment ScannerAssessment) ScannerAssessment {
\t// Repaired path: scanner health and DB-revision facts remain authoritative.
\treturn assessment
}''',
    )
    SOL_PLATFORM.mkdir(parents=True, exist_ok=True)
    (SOL_PLATFORM / "evidence_runtime.go").write_text(text)


def materialize_journal_runtime() -> None:
    text = (ENV_PLATFORM / "journal_runtime.go").read_text()
    text = replace_function(
        text,
        "func CommitAdmissionDecision",
        "func JournalRequestHistory",
        '''func CommitAdmissionDecision(context *EvaluationContext, decision Decision) (Decision, error) {
\tplan, err := BuildDecisionCommitPlan(context, decision)
\tif err != nil {
\t\treturn decision, err
\t}
\tcontext.AddTrace(StagePersistence, "JOURNAL_INSPECTED", journalInspectionSummary(plan.Inspection))
\tif plan.Inspection.InteriorCorruption || len(plan.Inspection.MalformedLines) > 0 {
\t\treturn decision, fmt.Errorf("audit journal corruption: %s", JournalCorruptionDescription(plan.Inspection))
\t}
\tif plan.DuplicateDecision && plan.Existing != nil {
\t\tcontext.AddTrace(StagePersistence, "IDEMPOTENT_REPLAY", plan.Existing.DecisionID)
\t\tif err := WriteLastDecision(context.Paths.Root, *plan.Existing); err != nil {
\t\t\treturn decision, err
\t\t}
\t\treturn *plan.Existing, nil
\t}
\t// Durable journal is authoritative: fsync it before advancing the derived
\t// last-decision projection.
\tif err := AppendAudit(context.Paths.Root, decision); err != nil {
\t\treturn decision, err
\t}
\tcontext.AddTrace(StagePersistence, "JOURNAL_DURABLE", decision.DecisionID)
\tif err := WriteLastDecision(context.Paths.Root, decision); err != nil {
\t\treturn decision, err
\t}
\tcontext.AddTrace(StagePersistence, "PROJECTION_WRITTEN", decision.DecisionID)
\treturn decision, nil
}''',
    )
    (SOL_PLATFORM / "journal_runtime.go").write_text(text)


def materialize_engine() -> None:
    (SOL_PLATFORM / "engine.go").write_text('''package platform

import (
    "fmt"
    "time"
)

func decisionIDFromContext(context *EvaluationContext, code string) string {
    return stableID(
        context.Fingerprint(),
        context.SnapshotID,
        code,
        context.Now.UTC().Format(time.RFC3339),
    )
}

func baseContextDecision(context *EvaluationContext, verdict, code, message string) Decision {
    req := context.Request()
    return Decision{
        DecisionID:     decisionIDFromContext(context, code),
        RequestID:      req.RequestID,
        Decision:       verdict,
        Code:           code,
        Message:        message,
        PolicyVersion:  context.Compiled.Version,
        ArtifactDigest: req.Digest,
        EvaluatedAt:    context.Now.UTC().Format(time.RFC3339),
    }
}

func commitContextDecision(context *EvaluationContext, decision Decision) (Decision, error) {
    context.AddTrace(StageDecision, decision.Code, decision.Decision)
    return CommitAdmissionDecision(context, decision)
}

func denyContext(context *EvaluationContext, code, message string) (Decision, error) {
    return commitContextDecision(context, baseContextDecision(context, "DENY", code, message))
}

func allowContextWithException(context *EvaluationContext, exception Exception, evidence EvidenceAssessment, secret []byte) (Decision, error) {
    decision := baseContextDecision(context, "ALLOW", "ALLOW_EXCEPTION", "artifact vulnerability is covered by an exact, current exception")
    decision.ExceptionID = exception.ID
    decision.ScanDBRevision = evidence.ScannerDBRevision
    decision.CacheHit = evidence.CacheHit
    decision.Vulnerabilities = append([]Vulnerability(nil), evidence.Vulnerabilities...)
    issued := IssueAdmissionPermit(context, secret)
    decision.Permit = &issued.Permit
    return commitContextDecision(context, decision)
}

func allowContextClean(context *EvaluationContext, evidence EvidenceAssessment, secret []byte) (Decision, error) {
    decision := baseContextDecision(context, "ALLOW", "ALLOW_CLEAN", "artifact satisfies current software policy")
    decision.ScanDBRevision = evidence.ScannerDBRevision
    decision.CacheHit = evidence.CacheHit
    decision.Vulnerabilities = append([]Vulnerability(nil), evidence.Vulnerabilities...)
    issued := IssueAdmissionPermit(context, secret)
    decision.Permit = &issued.Permit
    return commitContextDecision(context, decision)
}

func denyFromEvidence(context *EvaluationContext, evidence EvidenceAssessment) (Decision, error) {
    decision := baseContextDecision(context, "DENY", evidence.FailureCode, evidence.FailureMessage)
    decision.ScanDBRevision = evidence.ScannerDBRevision
    decision.CacheHit = evidence.CacheHit
    decision.Vulnerabilities = append([]Vulnerability(nil), evidence.Vulnerabilities...)
    return commitContextDecision(context, decision)
}

func denyFromVulnerability(context *EvaluationContext, evidence EvidenceAssessment, vulnerability VulnerabilityDecision) (Decision, error) {
    decision := baseContextDecision(context, "DENY", vulnerability.FailureCode, vulnerability.FailureMessage)
    decision.ScanDBRevision = evidence.ScannerDBRevision
    decision.CacheHit = evidence.CacheHit
    decision.Vulnerabilities = append([]Vulnerability(nil), evidence.Vulnerabilities...)
    return commitContextDecision(context, decision)
}

func Evaluate(policy Policy, scans ScanDB, exceptions ExceptionDB, req Request, stateDir string, secret []byte, now time.Time) (Decision, error) {
    context, err := PrepareEvaluation(policy, req, stateDir, now)
    if err != nil {
        return Decision{}, err
    }
    if len(secret) == 0 {
        return Decision{}, fmt.Errorf("permit secret is empty")
    }

    lock, err := AcquireStateHandle(stateDir)
    if err != nil {
        return Decision{}, err
    }
    defer lock.Close()

    // Recover only an incomplete final write before inspecting durable state.
    // Interior corruption remains a hard error in CommitAdmissionDecision.
    if err := RecoverAuditLegacy(stateDir); err != nil {
        return Decision{}, err
    }
    state, err := PrepareStateRuntime(context)
    if err != nil {
        return Decision{}, err
    }
    if err := ValidateStateForMutation(state); err != nil {
        return Decision{}, err
    }

    digest := EvaluateDigestPolicy(context)
    if digest.FailureCode != "" {
        context.AddTrace(StageIdentity, digest.FailureCode, digest.FailureMessage)
        return denyContext(context, digest.FailureCode, digest.FailureMessage)
    }
    context.AddTrace(StageIdentity, "DIGEST_ACCEPTED", context.Request().Digest)

    source := EvaluateSourcePolicy(context)
    if !source.Allowed {
        context.AddTrace(StageSource, source.FailureCode, source.FailureMessage)
        return denyContext(context, source.FailureCode, source.FailureMessage)
    }
    context.AddTrace(StageSource, "SOURCE_ACCEPTED", fmt.Sprintf("%s:%s", source.MatchKind, source.Canonical))

    evidence, err := ResolveEvidence(context, scans, stateDir)
    if err != nil {
        return Decision{}, err
    }
    if EvidenceRequiresDeny(evidence) {
        return denyFromEvidence(context, evidence)
    }

    vulnerability := EvaluateVulnerabilityPolicy(context, evidence.Vulnerabilities)
    if vulnerability.Denied {
        exception := EvaluateExceptionPolicy(context, exceptions, "VULNERABILITY_THRESHOLD")
        if ExceptionAllows(exception) {
            return allowContextWithException(context, *exception.Matched, evidence, secret)
        }
        return denyFromVulnerability(context, evidence, vulnerability)
    }
    return allowContextClean(context, evidence, secret)
}
''')


def materialize_solve() -> None:
    (SOL / "solve.sh").write_text('''#!/usr/bin/env bash
set -euo pipefail
ROOT="${ENFORCER_ROOT:-/app/enforcer}"
SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"
BIN_OUT="${ARTIFACTGUARD_BIN:-/usr/local/bin/artifactguard}"
install -m 0644 "$SOLUTION_ROOT/files/platform/policy.go" "$ROOT/internal/platform/policy.go"
install -m 0644 "$SOLUTION_ROOT/files/platform/cache.go" "$ROOT/internal/platform/cache.go"
install -m 0644 "$SOLUTION_ROOT/files/platform/exceptions.go" "$ROOT/internal/platform/exceptions.go"
install -m 0644 "$SOLUTION_ROOT/files/platform/permit.go" "$ROOT/internal/platform/permit.go"
install -m 0644 "$SOLUTION_ROOT/files/platform/state.go" "$ROOT/internal/platform/state.go"
install -m 0644 "$SOLUTION_ROOT/files/platform/audit.go" "$ROOT/internal/platform/audit.go"
install -m 0644 "$SOLUTION_ROOT/files/platform/replay.go" "$ROOT/internal/platform/replay.go"
install -m 0644 "$SOLUTION_ROOT/files/platform/evidence_runtime.go" "$ROOT/internal/platform/evidence_runtime.go"
install -m 0644 "$SOLUTION_ROOT/files/platform/journal_runtime.go" "$ROOT/internal/platform/journal_runtime.go"
install -m 0644 "$SOLUTION_ROOT/files/platform/engine.go" "$ROOT/internal/platform/engine.go"
install -m 0644 "$SOLUTION_ROOT/files/core/engine.go" "$ROOT/internal/core/engine.go"
install -m 0644 "$SOLUTION_ROOT/files/cmd/main.go" "$ROOT/cmd/artifactguard/main.go"
cd "$ROOT"
gofmt -w cmd/artifactguard/main.go internal/core/engine.go internal/platform/policy.go internal/platform/cache.go internal/platform/exceptions.go internal/platform/permit.go internal/platform/state.go internal/platform/audit.go internal/platform/replay.go internal/platform/evidence_runtime.go internal/platform/journal_runtime.go internal/platform/engine.go
go test ./...
go build -o "$BIN_OUT" ./cmd/artifactguard
''')


def main() -> None:
    materialize_evidence_runtime()
    materialize_journal_runtime()
    materialize_engine()
    materialize_solve()


if __name__ == "__main__":
    main()
