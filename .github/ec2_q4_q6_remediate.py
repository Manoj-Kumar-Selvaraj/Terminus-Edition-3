#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "ec2-artifact-policy-enforcement"
PLATFORM = TASK / "environment" / "enforcer" / "internal" / "platform"
MAP = ROOT / ".terminus" / "designs" / "ec2-artifact-policy-enforcement-test-map.json"
Q4_TESTS = TASK / "tests" / "test_q4_contract_gaps.py"


def replace_once(path: Path, old: str, new: str) -> bool:
    text = path.read_text()
    if old not in text:
        return False
    path.write_text(text.replace(old, new, 1))
    return True


def patch_manager_compatibility() -> None:
    path = PLATFORM / "manager_profiles.go"
    replace_once(
        path,
        '\tcase "maven-coordinate":\n\t\treturn mavenNameRE.MatchString(name)\n\tcase "npm-package":',
        '\tcase "maven-coordinate":\n\t\tif strings.Contains(name, ":") {\n\t\t\treturn mavenNameRE.MatchString(name)\n\t\t}\n\t\treturn rpmNameRE.MatchString(name)\n\tcase "npm-package":',
    )
    replace_once(
        path,
        '\tcase "go-module":\n\t\treturn goModuleRE.MatchString(name) && strings.Contains(name, "/")',
        '\tcase "go-module":\n\t\treturn goModuleRE.MatchString(name)',
    )
    replace_once(
        path,
        '''func profileAllowsAction(profile ManagerProfile, action string) bool {
\taction = strings.ToLower(strings.TrimSpace(action))
\tif action == "" {
\t\treturn profile.AllowEmptyAction
\t}
\treturn contains(profile.InstallActions, action) || contains(profile.UpdateActions, action) || contains(profile.RemoveActions, action)
}''',
        '''func profileAllowsAction(profile ManagerProfile, action string) bool {
\taction = strings.ToLower(strings.TrimSpace(action))
\tif action == "" {
\t\treturn profile.AllowEmptyAction
\t}
\t// The external request contract uses "install" as the generic admission
\t// operation for all three surfaces; manager-specific verbs are accepted in
\t// addition to that stable compatibility action.
\tif action == "install" && profile.DefaultActionClass == "install" {
\t\treturn true
\t}
\treturn contains(profile.InstallActions, action) || contains(profile.UpdateActions, action) || contains(profile.RemoveActions, action)
}''',
    )


def patch_starter_scanner_seam() -> None:
    path = PLATFORM / "evidence_runtime.go"
    old = '''func legacyScannerRecord(context *EvaluationContext, assessment ScannerAssessment) ScannerAssessment {
\tif assessment.Healthy {
\t\treturn assessment
\t}
\t// Intentional starter defect: unavailable scanner evidence is transformed
\t// into a current clean record instead of failing closed.  The solution
\t// removes this conversion.
\tassessment.Healthy = true
\tassessment.RevisionMatches = true
\tassessment.Status = "ok"
\tassessment.DBRevision = context.Compiled.ScannerRevision
\tassessment.Vulnerabilities = nil
\tassessment.MaximumSeverity = "NONE"
\tassessment.Reason = "legacy-fail-open-clean"
\treturn assessment
}'''
    new = '''func legacyScannerRecord(context *EvaluationContext, assessment ScannerAssessment) ScannerAssessment {
\tif !assessment.Healthy {
\t\t// Intentional starter defect: unavailable scanner evidence is transformed
\t\t// into a current clean record instead of failing closed.  The solution
\t\t// removes this conversion.
\t\tassessment.Healthy = true
\t\tassessment.RevisionMatches = true
\t\tassessment.Status = "ok"
\t\tassessment.DBRevision = context.Compiled.ScannerRevision
\t\tassessment.Vulnerabilities = nil
\t\tassessment.MaximumSeverity = "NONE"
\t\tassessment.Reason = "legacy-fail-open-clean"
\t\treturn assessment
\t}
\tif !assessment.RevisionMatches {
\t\t// Intentional starter defect: a healthy record from a stale scanner DB
\t\t// is accepted as if it were current.
\t\tassessment.RevisionMatches = true
\t\tassessment.Reason = "legacy-stale-revision-accepted"
\t}
\treturn assessment
}'''
    replace_once(path, old, new)


def write_q4_tests() -> None:
    Q4_TESTS.write_text('''from __future__ import annotations

import copy

from verifier_lib import (
    base_policy,
    case_dir,
    exception_for,
    find_digest,
    issue_clean_permit,
    make_request,
    run_evaluate,
    run_verify,
    trusted_source,
)


def test_f2p_exact_exception_cannot_override_untrusted_source():
    """An exact vulnerability exception cannot waive the trusted-source prerequisite."""
    with case_dir() as root:
        policy = base_policy()
        digest = find_digest(vulnerable=True)
        req = make_request("req-ex-source-order", "package", "apt", digest, "attacker.invalid/repo")
        ex = exception_for(req)
        cp, out, _ = run_evaluate(root, req, policy=policy, exceptions={"exceptions": [ex]})
        assert cp.returncode == 42 and out["code"] == "DENY_UNTRUSTED_SOURCE"


def test_p2p_permit_request_id_mismatch_remains_invalid():
    """Changing request_id must continue to invalidate an otherwise intact permit."""
    with case_dir() as root:
        permit, req, policy = issue_clean_permit(root / "issue")
        changed = copy.deepcopy(req)
        changed["request_id"] = req["request_id"] + "-different"
        cp, out = run_verify(permit, changed, policy, b"verifier-secret-a", work=root / "verify")
        assert cp.returncode == 43 and out["valid"] is False


def test_p2p_permit_policy_version_mismatch_remains_invalid():
    """Changing policy version must continue to invalidate an otherwise intact permit."""
    with case_dir() as root:
        permit, req, policy = issue_clean_permit(root / "issue")
        changed_policy = copy.deepcopy(policy)
        changed_policy["version"] = policy["version"] + "-different"
        cp, out = run_verify(permit, req, changed_policy, b"verifier-secret-a", work=root / "verify")
        assert cp.returncode == 43 and out["valid"] is False


def test_p2p_wrong_exception_policy_code_remains_non_authorizing():
    """An exception for another policy code must not waive vulnerability threshold denial."""
    with case_dir() as root:
        policy = base_policy()
        digest = find_digest(vulnerable=True)
        req = make_request("req-ex-code", "package", "apt", digest, trusted_source("package", policy))
        ex = exception_for(req, codes=["SOURCE_POLICY"])
        cp, out, _ = run_evaluate(root, req, policy=policy, exceptions={"exceptions": [ex]})
        assert cp.returncode == 42 and out["code"] == "DENY_VULNERABLE"
''')


def update_test_map() -> None:
    data = json.loads(MAP.read_text())
    additions = [
        ["test_f2p_exact_exception_cannot_override_untrusted_source", "F2P", "REQ_SOURCE_DIGEST", "F2P-SRC-05"],
        ["test_p2p_permit_request_id_mismatch_remains_invalid", "P2P", "REQ_PRESERVATION", "P2P-10"],
        ["test_p2p_permit_policy_version_mismatch_remains_invalid", "P2P", "REQ_PRESERVATION", "P2P-11"],
        ["test_p2p_wrong_exception_policy_code_remains_non_authorizing", "P2P", "REQ_PRESERVATION", "P2P-12"],
    ]
    existing = {row[0] for row in data["tests"]}
    for row in additions:
        if row[0] not in existing:
            data["tests"].append(row)
    dimensions = data.setdefault("behavioral_dimensions", {})
    cross = dimensions.setdefault("cross_component", [])
    if "F2P-SRC-05" not in cross:
        cross.append("F2P-SRC-05")
    normal = dimensions.setdefault("normal", [])
    for case_id in ("P2P-10", "P2P-11", "P2P-12"):
        if case_id not in normal:
            normal.append(case_id)
    organic = data.get("organic_count_justification", "")
    data["organic_count_justification"] = organic.replace("The 27 F2P cases", "The 28 F2P cases")
    MAP.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    patch_manager_compatibility()
    patch_starter_scanner_seam()
    write_q4_tests()
    update_test_map()


if __name__ == "__main__":
    main()
