import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(os.environ.get("ENFORCER_ROOT", "/app/enforcer"))
BIN = os.environ.get("AG_BIN", "/usr/local/bin/artifactguard")
NOW = "2026-08-17T12:00:00Z"
CLEAN_PKG = "sha256:" + "1" * 64
VULN_PKG = "sha256:" + "2" * 64
CLEAN_IMG = "sha256:" + "3" * 64
VULN_IMG = "sha256:" + "4" * 64
CLEAN_DEP = "sha256:" + "5" * 64
VULN_DEP = "sha256:" + "6" * 64
UNAVAILABLE = "sha256:" + "7" * 64


def load(name):
    return json.loads((ROOT / name).read_text())


def request(req_id, surface, manager, name, version, source, digest, env="production", instance="i-0abc123"):
    return {
        "request_id": req_id,
        "instance_id": instance,
        "environment": env,
        "surface": surface,
        "manager": manager,
        "name": name,
        "version": version,
        "source": source,
        "digest": digest,
        "action": "acquire",
    }


def write(path, value):
    path.write_text(json.dumps(value))


def run_eval(tmp_path, req, *, policy=None, scans=None, exceptions=None, now=NOW, state=None, secret=b"fixture-secret"):
    policy = copy.deepcopy(policy or load("config/policy.json"))
    scans = copy.deepcopy(scans or load("fixtures/scans.json"))
    exceptions = copy.deepcopy(exceptions or load("fixtures/exceptions.json"))
    state = Path(state or (tmp_path / "state"))
    state.mkdir(parents=True, exist_ok=True)
    req_path = tmp_path / "request.json"
    policy_path = tmp_path / "policy.json"
    scans_path = tmp_path / "scans.json"
    exceptions_path = tmp_path / "exceptions.json"
    secret_path = tmp_path / "secret.key"
    write(req_path, req)
    write(policy_path, policy)
    write(scans_path, scans)
    write(exceptions_path, exceptions)
    secret_path.write_bytes(secret)
    proc = subprocess.run([
        BIN, "evaluate", "--request", str(req_path), "--policy", str(policy_path), "--scans", str(scans_path),
        "--exceptions", str(exceptions_path), "--state", str(state), "--secret", str(secret_path), "--now", now,
    ], text=True, capture_output=True)
    assert proc.returncode in (0, 42), proc.stderr
    return proc.returncode, json.loads(proc.stdout), state, policy_path, secret_path


def run_verify(tmp_path, permit, req, policy, secret=b"fixture-secret", now=NOW):
    permit_path = tmp_path / "permit.json"
    req_path = tmp_path / "verify-request.json"
    policy_path = tmp_path / "verify-policy.json"
    secret_path = tmp_path / "verify-secret.key"
    write(permit_path, permit)
    write(req_path, req)
    write(policy_path, policy)
    secret_path.write_bytes(secret)
    proc = subprocess.run([BIN, "verify-permit", "--permit", str(permit_path), "--request", str(req_path), "--policy", str(policy_path), "--secret", str(secret_path), "--now", now], text=True, capture_output=True)
    assert proc.returncode in (0, 43), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def vuln_record(db_revision="trivy-db-2026-08-17"):
    return {"status": "ok", "db_revision": db_revision, "vulnerabilities": [{"id": "CVE-2099-9999", "severity": "CRITICAL"}]}


def test_clean_os_package_is_allowed(tmp_path):
    req = request("pkg-clean", "package", "apt", "curl", "8.5", "ubuntu-main", CLEAN_PKG)
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 0 and out["decision"] == "ALLOW" and out["code"] == "ALLOW_CLEAN" and out["permit"]


def test_vulnerable_os_package_is_denied(tmp_path):
    req = request("pkg-vuln", "package", "apt", "openssl", "3", "ubuntu-main", VULN_PKG)
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_VULNERABLE"


def test_scanner_unavailable_fails_closed(tmp_path):
    req = request("pkg-no-scan", "package", "apt", "tool", "1", "ubuntu-main", UNAVAILABLE)
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_SCANNER_UNAVAILABLE"


@pytest.mark.parametrize("manager", ["dpkg", "rpm"])
def test_direct_package_installers_cannot_bypass_source_policy(tmp_path, manager):
    req = request("direct-" + manager, "package", manager, "vendor-agent", "1", "file:///tmp/vendor.pkg", CLEAN_PKG)
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_UNTRUSTED_SOURCE"


def test_container_missing_digest_is_denied(tmp_path):
    req = request("img-no-digest", "container", "docker", "payments", "stable", "public.ecr.aws", "")
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_MISSING_DIGEST"


def test_mutable_image_tag_does_not_reuse_other_digest_scan(tmp_path):
    state = tmp_path / "state"
    first = request("img-clean", "container", "docker", "payments", "stable", "public.ecr.aws", CLEAN_IMG)
    rc1, out1, *_ = run_eval(tmp_path, first, state=state)
    assert rc1 == 0 and out1["code"] == "ALLOW_CLEAN"
    second = request("img-moved", "container", "docker", "payments", "stable", "public.ecr.aws", VULN_IMG)
    rc2, out2, *_ = run_eval(tmp_path, second, state=state)
    assert rc2 == 42 and out2["code"] == "DENY_VULNERABLE" and out2["cache_hit"] is False


def test_build_dependency_uses_source_policy(tmp_path):
    req = request("dep-source", "dependency", "maven", "com.example:lib", "1.0", "repo.bad.invalid", CLEAN_DEP)
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_UNTRUSTED_SOURCE"


def test_vulnerable_build_dependency_is_denied(tmp_path):
    req = request("dep-vuln", "dependency", "maven", "com.example:legacy", "1.0", "repo.maven.apache.org", VULN_DEP)
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_VULNERABLE"


def test_valid_scoped_exception_allows_only_matching_request(tmp_path):
    req = request("pkg-exception", "package", "apt", "openssl", "3", "ubuntu-main", VULN_PKG, env="staging")
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 0 and out["code"] == "ALLOW_EXCEPTION" and out["exception_id"] == "SEC-100"


def test_expired_exception_is_rejected(tmp_path):
    req = request("dep-expired", "dependency", "maven", "legacy", "1", "repo.maven.apache.org", VULN_DEP, env="production")
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_VULNERABLE"


def test_wrong_environment_exception_is_rejected(tmp_path):
    req = request("img-wrong-env", "container", "docker", "payments", "bad", "public.ecr.aws", VULN_IMG, env="production")
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 42 and out["code"] == "DENY_VULNERABLE"


def test_policy_version_change_invalidates_cache(tmp_path):
    state = tmp_path / "state"
    req = request("policy-cache", "package", "apt", "curl", "8.5", "ubuntu-main", CLEAN_PKG)
    rc1, _, *_ = run_eval(tmp_path, req, state=state)
    assert rc1 == 0
    policy = load("config/policy.json")
    policy["version"] = "policy-2026-08-17-b"
    scans = load("fixtures/scans.json")
    scans["records"][CLEAN_PKG] = vuln_record()
    rc2, out2, *_ = run_eval(tmp_path, req, policy=policy, scans=scans, state=state)
    assert rc2 == 42 and out2["code"] == "DENY_VULNERABLE" and out2["cache_hit"] is False


def test_scanner_db_revision_change_invalidates_cache(tmp_path):
    state = tmp_path / "state"
    req = request("db-cache", "package", "apt", "curl", "8.5", "ubuntu-main", CLEAN_PKG)
    rc1, _, *_ = run_eval(tmp_path, req, state=state)
    assert rc1 == 0
    policy = load("config/policy.json")
    policy["scanner_db_revision"] = "trivy-db-2026-08-18"
    scans = load("fixtures/scans.json")
    scans["records"][CLEAN_PKG] = vuln_record("trivy-db-2026-08-18")
    rc2, out2, *_ = run_eval(tmp_path, req, policy=policy, scans=scans, state=state)
    assert rc2 == 42 and out2["code"] == "DENY_VULNERABLE" and out2["cache_hit"] is False


def test_expired_cache_is_not_reused(tmp_path):
    state = tmp_path / "state"
    req = request("ttl-cache", "package", "apt", "curl", "8.5", "ubuntu-main", CLEAN_PKG)
    rc1, _, *_ = run_eval(tmp_path, req, state=state, now="2026-08-17T10:00:00Z")
    assert rc1 == 0
    scans = load("fixtures/scans.json")
    scans["records"][CLEAN_PKG] = vuln_record()
    rc2, out2, *_ = run_eval(tmp_path, req, scans=scans, state=state, now="2026-08-17T12:00:01Z")
    assert rc2 == 42 and out2["cache_hit"] is False


def test_exact_fresh_cache_survives_process_restart(tmp_path):
    state = tmp_path / "state"
    req = request("restart-cache", "dependency", "pip", "requests", "2", "pypi.org", CLEAN_DEP)
    rc1, _, *_ = run_eval(tmp_path, req, state=state, now="2026-08-17T10:00:00Z")
    assert rc1 == 0
    scans = load("fixtures/scans.json")
    scans["records"][CLEAN_DEP] = {"status": "unavailable", "db_revision": "trivy-db-2026-08-17", "vulnerabilities": []}
    rc2, out2, *_ = run_eval(tmp_path, req, scans=scans, state=state, now="2026-08-17T10:05:00Z")
    assert rc2 == 0 and out2["cache_hit"] is True


def test_stale_scanner_revision_is_denied(tmp_path):
    req = request("stale-scan", "package", "apt", "curl", "8.5", "ubuntu-main", CLEAN_PKG)
    policy = load("config/policy.json")
    policy["scanner_db_revision"] = "trivy-db-2026-08-18"
    rc, out, *_ = run_eval(tmp_path, req, policy=policy)
    assert rc == 42 and out["code"] == "DENY_SCANNER_EVIDENCE_STALE"


def test_denies_and_allows_are_both_durable_in_audit(tmp_path):
    state = tmp_path / "state"
    allow = request("audit-allow", "package", "apt", "curl", "8.5", "ubuntu-main", CLEAN_PKG)
    deny = request("audit-deny", "package", "apt", "openssl", "3", "ubuntu-main", VULN_PKG)
    run_eval(tmp_path, allow, state=state)
    run_eval(tmp_path, deny, state=state)
    rows = [json.loads(line) for line in (state / "audit.jsonl").read_text().splitlines()]
    by_id = {row["request_id"]: row["decision"] for row in rows}
    assert by_id["audit-allow"] == "ALLOW" and by_id["audit-deny"] == "DENY"


def test_forged_unkeyed_permit_is_rejected(tmp_path):
    req = request("permit-forge", "package", "apt", "curl", "8.5", "ubuntu-main", CLEAN_PKG)
    rc, out, *_ = run_eval(tmp_path, req)
    assert rc == 0
    forged_req = dict(req)
    forged_req["instance_id"] = "i-attacker"
    permit = dict(out["permit"])
    permit["instance_id"] = "i-attacker"
    payload = "|".join([permit["request_id"], permit["instance_id"], permit["artifact_digest"], permit["policy_version"], permit["expires_at"]])
    permit["signature"] = hashlib.sha256(payload.encode()).hexdigest()
    vrc, result = run_verify(tmp_path, permit, forged_req, load("config/policy.json"))
    assert vrc == 43 and result["valid"] is False


def test_expired_permit_is_rejected(tmp_path):
    req = request("permit-expired", "package", "apt", "curl", "8.5", "ubuntu-main", CLEAN_PKG)
    rc, out, *_ = run_eval(tmp_path, req, now="2026-08-17T10:00:00Z")
    assert rc == 0
    vrc, result = run_verify(tmp_path, out["permit"], req, load("config/policy.json"), now="2026-08-17T10:06:00Z")
    assert vrc == 43 and result["code"] == "PERMIT_EXPIRED"
