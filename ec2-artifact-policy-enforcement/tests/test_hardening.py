import json

import pytest

from test_outputs import (
    CLEAN_DEP,
    CLEAN_IMG,
    CLEAN_PKG,
    UNAVAILABLE,
    VULN_PKG,
    load,
    request,
    run_eval,
    run_verify,
)


def test_untrusted_container_registry_is_denied(tmp_path):
    req = request(
        "img-untrusted-registry",
        "container",
        "docker",
        "payments",
        "stable",
        "registry.bad.invalid",
        CLEAN_IMG,
    )
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_UNTRUSTED_SOURCE"


@pytest.mark.parametrize(
    ("manager", "source"),
    [
        ("pip", "python.bad.invalid"),
        ("npm", "npm.bad.invalid"),
    ],
)
def test_direct_dependency_managers_cannot_bypass_source_policy(
    tmp_path, manager, source
):
    req = request(
        f"dep-direct-{manager}",
        "dependency",
        manager,
        "example-lib",
        "1.0",
        source,
        CLEAN_DEP,
    )
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_UNTRUSTED_SOURCE"


def test_exception_cannot_override_scanner_unavailable(tmp_path):
    exceptions = load("fixtures/exceptions.json")
    exceptions["exceptions"].append(
        {
            "id": "SEC-NO-SCAN",
            "digest": UNAVAILABLE,
            "surfaces": ["package"],
            "environments": ["staging"],
            "policy_codes": ["VULNERABILITY_THRESHOLD"],
            "expires_at": "2026-08-18T00:00:00Z",
        }
    )
    req = request(
        "exception-no-scan",
        "package",
        "apt",
        "vendor-tool",
        "1",
        "ubuntu-main",
        UNAVAILABLE,
        env="staging",
    )
    rc, out, *_ = run_eval(tmp_path, req, exceptions=exceptions)
    assert rc == 42 and out["code"] == "DENY_SCANNER_UNAVAILABLE"


def test_exception_cannot_override_stale_scanner_evidence(tmp_path):
    policy = load("config/policy.json")
    policy["scanner_db_revision"] = "trivy-db-2026-08-18"
    req = request(
        "exception-stale-scan",
        "package",
        "apt",
        "openssl",
        "3",
        "ubuntu-main",
        VULN_PKG,
        env="staging",
    )
    rc, out, *_ = run_eval(tmp_path, req, policy=policy)
    assert rc == 42 and out["code"] == "DENY_SCANNER_EVIDENCE_STALE"


def test_cache_identity_is_digest_not_package_name_or_version(tmp_path):
    state = tmp_path / "state"
    first = request(
        "cache-digest-first",
        "dependency",
        "pip",
        "requests",
        "2.32.0",
        "pypi.org",
        CLEAN_DEP,
    )
    rc1, out1, *_ = run_eval(
        tmp_path, first, state=state, now="2026-08-17T10:00:00Z"
    )
    assert rc1 == 0 and out1["cache_hit"] is False

    scans = load("fixtures/scans.json")
    scans["records"][CLEAN_DEP] = {
        "status": "unavailable",
        "db_revision": "trivy-db-2026-08-17",
        "vulnerabilities": [],
    }
    second = request(
        "cache-digest-second",
        "dependency",
        "pip",
        "renamed-wrapper",
        "99.0",
        "pypi.org",
        CLEAN_DEP,
    )
    rc2, out2, *_ = run_eval(
        tmp_path,
        second,
        scans=scans,
        state=state,
        now="2026-08-17T10:05:00Z",
    )
    assert rc2 == 0 and out2["code"] == "ALLOW_CLEAN"
    assert out2["cache_hit"] is True


def test_permit_rejects_wrong_secret(tmp_path):
    req = request(
        "permit-secret",
        "package",
        "apt",
        "curl",
        "8.5",
        "ubuntu-main",
        CLEAN_PKG,
    )
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 0
    vrc, result = run_verify(
        tmp_path,
        out["permit"],
        req,
        load("config/policy.json"),
        secret=b"different-host-secret",
    )
    assert vrc == 43 and result["valid"] is False
    assert result["code"] == "PERMIT_SIGNATURE_INVALID"


def test_permit_is_bound_to_instance_even_without_rewriting_permit(tmp_path):
    req = request(
        "permit-instance",
        "package",
        "apt",
        "curl",
        "8.5",
        "ubuntu-main",
        CLEAN_PKG,
    )
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 0
    other_instance = dict(req)
    other_instance["instance_id"] = "i-0different"
    vrc, result = run_verify(
        tmp_path,
        out["permit"],
        other_instance,
        load("config/policy.json"),
    )
    assert vrc == 43 and result["valid"] is False
    assert result["code"] == "PERMIT_SCOPE_MISMATCH"


def test_audit_history_preserves_order_across_process_restarts(tmp_path):
    state = tmp_path / "state"
    requests = [
        request(
            "audit-restart-allow-1",
            "package",
            "apt",
            "curl",
            "8.5",
            "ubuntu-main",
            CLEAN_PKG,
        ),
        request(
            "audit-restart-deny",
            "package",
            "apt",
            "openssl",
            "3",
            "ubuntu-main",
            VULN_PKG,
        ),
        request(
            "audit-restart-allow-2",
            "container",
            "docker",
            "payments",
            "stable",
            "public.ecr.aws",
            CLEAN_IMG,
        ),
    ]
    for req in requests:
        run_eval(tmp_path, req, state=state)

    rows = [
        json.loads(line)
        for line in (state / "audit.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert [row["request_id"] for row in rows] == [
        "audit-restart-allow-1",
        "audit-restart-deny",
        "audit-restart-allow-2",
    ]
    assert [row["decision"] for row in rows] == ["ALLOW", "DENY", "ALLOW"]
    last = json.loads((state / "last-decision.json").read_text())
    assert last["request_id"] == "audit-restart-allow-2"
    assert last["decision"] == "ALLOW"
