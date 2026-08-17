import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(os.environ.get("POLICYGUARD_ROOT", "/app/policyguard"))
BINARY = ROOT / "target" / "release" / "policyguard"
PACKAGE_WRAPPER = ROOT / "bin" / "policy-package"
CONTAINER_WRAPPER = ROOT / "bin" / "policy-container"
DEPENDENCY_WRAPPER = ROOT / "bin" / "policy-dependency"
BASE_CONFIG = ROOT / "config" / "policy.conf"
BASE_SCAN_DB = ROOT / "config" / "scan-db.tsv"
BASE_EXCEPTIONS = ROOT / "config" / "exceptions.tsv"
NOW = 1_786_970_000


@dataclass
class Runtime:
    config: Path
    scan_db: Path
    exceptions: Path
    state: Path


@pytest.fixture
def runtime(tmp_path: Path) -> Runtime:
    config = tmp_path / "policy.conf"
    scan_db = tmp_path / "scan-db.tsv"
    exceptions = tmp_path / "exceptions.tsv"
    state = tmp_path / "state"
    shutil.copy2(BASE_CONFIG, config)
    shutil.copy2(BASE_SCAN_DB, scan_db)
    shutil.copy2(BASE_EXCEPTIONS, exceptions)
    state.mkdir()
    return Runtime(config=config, scan_db=scan_db, exceptions=exceptions, state=state)


def _invoke(
    runtime: Runtime,
    *,
    executable: Path = BINARY,
    kind: str = "package",
    name: str = "curl",
    version: str = "8.0",
    source: str = "ubuntu-main",
    digest: str = "sha256:pkg-clean",
    instance: str = "i-builder-001",
    environment: str = "prod",
    now: int = NOW,
    signed: bool = True,
    scanner_status: str = "normal",
) -> tuple[subprocess.CompletedProcess[str], dict]:
    command = [str(executable)]
    if executable == BINARY:
        command += ["evaluate", "--kind", kind]
    command += [
        "--name",
        name,
        "--version",
        version,
        "--source",
        source,
        "--digest",
        digest,
        "--instance",
        instance,
        "--environment",
        environment,
        "--now",
        str(now),
        "--signed",
        "true" if signed else "false",
        "--scanner-status",
        scanner_status,
        "--config",
        str(runtime.config),
        "--scan-db",
        str(runtime.scan_db),
        "--exceptions",
        str(runtime.exceptions),
        "--state-dir",
        str(runtime.state),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert completed.returncode in {0, 42}, completed.stderr
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines, f"no decision JSON; stderr={completed.stderr!r}"
    return completed, json.loads(lines[-1])


def _verify(
    runtime: Runtime,
    token: str,
    *,
    instance: str = "i-builder-001",
    digest: str = "sha256:pkg-clean",
    now: int = NOW,
) -> tuple[subprocess.CompletedProcess[str], dict]:
    completed = subprocess.run(
        [
            str(BINARY),
            "verify-permit",
            "--token",
            token,
            "--instance",
            instance,
            "--digest",
            digest,
            "--now",
            str(now),
            "--config",
            str(runtime.config),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode in {0, 43}, completed.stderr
    return completed, json.loads(completed.stdout.strip().splitlines()[-1])


def _set_config(path: Path, key: str, value: str) -> None:
    lines = path.read_text().splitlines()
    replaced = False
    output = []
    for line in lines:
        if line.startswith(f"{key}="):
            output.append(f"{key}={value}")
            replaced = True
        else:
            output.append(line)
    assert replaced, key
    path.write_text("\n".join(output) + "\n")


def _set_scan(path: Path, digest: str, severity: str) -> None:
    lines = path.read_text().splitlines()
    output = []
    replaced = False
    for line in lines:
        if line.startswith(f"{digest}\t"):
            output.append(f"{digest}\t{severity}")
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"{digest}\t{severity}")
    path.write_text("\n".join(output) + "\n")


def _assert_allow(result: dict, reason: str | None = None) -> None:
    assert result["decision"] == "ALLOW", result
    if reason is not None:
        assert result["reason"] == reason, result
    assert result["permit"], result


def _assert_deny(result: dict, reason: str) -> None:
    assert result["decision"] == "DENY", result
    assert result["reason"] == reason, result
    assert result["permit"] is None, result


def test_package_wrapper_allows_clean_trusted_package(runtime: Runtime) -> None:
    _, result = _invoke(runtime, executable=PACKAGE_WRAPPER)
    _assert_allow(result, "POLICY_ALLOW")


def test_package_blocks_critical_vulnerability(runtime: Runtime) -> None:
    _, result = _invoke(runtime, digest="sha256:pkg-vuln")
    _assert_deny(result, "VULNERABILITY_THRESHOLD_EXCEEDED")


def test_medium_severity_remains_allowed_at_high_threshold(runtime: Runtime) -> None:
    _, result = _invoke(runtime, digest="sha256:pkg-medium")
    _assert_allow(result, "POLICY_ALLOW")


def test_scanner_outage_fails_closed(runtime: Runtime) -> None:
    _, result = _invoke(runtime, scanner_status="unavailable")
    _assert_deny(result, "SCANNER_EVIDENCE_UNAVAILABLE")


def test_unknown_scanner_result_is_not_treated_as_clean(runtime: Runtime) -> None:
    _, result = _invoke(runtime, digest="sha256:not-in-database")
    _assert_deny(result, "SCANNER_RESULT_UNKNOWN")


def test_untrusted_package_repository_is_rejected(runtime: Runtime) -> None:
    _, result = _invoke(runtime, source="packages.example.invalid")
    _assert_deny(result, "UNTRUSTED_SOURCE")


def test_local_package_file_cannot_bypass_repository_policy(runtime: Runtime) -> None:
    _, result = _invoke(runtime, source="file:/tmp/custom.deb")
    _assert_deny(result, "UNTRUSTED_SOURCE")


def test_container_wrapper_allows_clean_signed_digest(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        executable=CONTAINER_WRAPPER,
        kind="container",
        name="orders-api",
        version="2026.08",
        source="public.ecr.aws",
        digest="sha256:image-clean",
        signed=True,
    )
    _assert_allow(result, "POLICY_ALLOW")


def test_container_requires_sha256_immutable_identity(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        kind="container",
        name="orders-api",
        version="latest",
        source="public.ecr.aws",
        digest="tag:latest",
    )
    _assert_deny(result, "IMMUTABLE_ID_REQUIRED")


def test_unsigned_container_is_rejected(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        kind="container",
        name="orders-api",
        version="2026.08",
        source="public.ecr.aws",
        digest="sha256:image-clean",
        signed=False,
    )
    _assert_deny(result, "CONTAINER_SIGNATURE_REQUIRED")


def test_untrusted_container_registry_is_rejected(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        kind="container",
        name="orders-api",
        version="2026.08",
        source="docker.io",
        digest="sha256:image-clean",
    )
    _assert_deny(result, "UNTRUSTED_SOURCE")


def test_container_tag_cache_cannot_hide_digest_change(runtime: Runtime) -> None:
    _, first = _invoke(
        runtime,
        kind="container",
        name="orders-api",
        version="stable",
        source="public.ecr.aws",
        digest="sha256:image-clean",
    )
    _assert_allow(first)
    _, second = _invoke(
        runtime,
        kind="container",
        name="orders-api",
        version="stable",
        source="public.ecr.aws",
        digest="sha256:image-vuln",
    )
    _assert_deny(second, "VULNERABILITY_THRESHOLD_EXCEEDED")
    assert second["cache_hit"] is False


def test_dependency_wrapper_allows_clean_approved_source(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        executable=DEPENDENCY_WRAPPER,
        kind="dependency",
        name="urllib3",
        version="2.5.0",
        source="pypi.corp.example",
        digest="sha256:dep-clean",
    )
    _assert_allow(result, "POLICY_ALLOW")


def test_dependency_blocks_high_vulnerability(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        kind="dependency",
        name="legacy-json",
        version="1.2.0",
        source="pypi.corp.example",
        digest="sha256:dep-vuln",
    )
    _assert_deny(result, "VULNERABILITY_THRESHOLD_EXCEEDED")


def test_direct_dependency_url_cannot_bypass_source_policy(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        kind="dependency",
        name="urllib3",
        version="2.5.0",
        source="https://files.example.invalid/urllib3.whl",
        digest="sha256:dep-clean",
    )
    _assert_deny(result, "UNTRUSTED_SOURCE")


def test_untrusted_dependency_repository_is_rejected(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        kind="dependency",
        name="urllib3",
        version="2.5.0",
        source="pypi.org",
        digest="sha256:dep-clean",
    )
    _assert_deny(result, "UNTRUSTED_SOURCE")


def test_exact_artifact_reuses_unexpired_cache(runtime: Runtime) -> None:
    _, first = _invoke(runtime)
    _assert_allow(first)
    _, second = _invoke(runtime, now=NOW + 10)
    _assert_allow(second)
    assert second["cache_hit"] is True


def test_expired_cache_is_rescanned(runtime: Runtime) -> None:
    _, first = _invoke(runtime, digest="sha256:rolling")
    _assert_allow(first)
    _set_scan(runtime.scan_db, "sha256:rolling", "CRITICAL")
    _, second = _invoke(runtime, digest="sha256:rolling", now=NOW + 3601)
    _assert_deny(second, "VULNERABILITY_THRESHOLD_EXCEEDED")
    assert second["cache_hit"] is False


def test_policy_generation_change_invalidates_cache(runtime: Runtime) -> None:
    _, first = _invoke(runtime, digest="sha256:pkg-medium")
    _assert_allow(first)
    _set_config(runtime.config, "policy_version", "policy-8")
    _set_config(runtime.config, "block_severity", "MEDIUM")
    _, second = _invoke(runtime, digest="sha256:pkg-medium", now=NOW + 1)
    _assert_deny(second, "VULNERABILITY_THRESHOLD_EXCEEDED")
    assert second["policy_version"] == "policy-8"
    assert second["cache_hit"] is False


def test_scanner_database_generation_change_invalidates_cache(runtime: Runtime) -> None:
    _, first = _invoke(runtime, digest="sha256:rolling")
    _assert_allow(first)
    _set_scan(runtime.scan_db, "sha256:rolling", "CRITICAL")
    _set_config(runtime.config, "scanner_db_version", "trivy-fixture-2026-08-17-b")
    _, second = _invoke(runtime, digest="sha256:rolling", now=NOW + 1)
    _assert_deny(second, "VULNERABILITY_THRESHOLD_EXCEEDED")
    assert second["scanner_db_version"].endswith("-b")
    assert second["cache_hit"] is False


def test_expired_security_exception_is_rejected(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        name="legacy-agent",
        version="4.1",
        digest="sha256:legacy-expired",
        environment="prod",
    )
    _assert_deny(result, "VULNERABILITY_THRESHOLD_EXCEEDED")


def test_security_exception_cannot_cross_environment(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        name="legacy-agent",
        version="4.1",
        digest="sha256:legacy-valid",
        environment="prod",
    )
    _assert_deny(result, "VULNERABILITY_THRESHOLD_EXCEEDED")


def test_security_exception_cannot_cross_digest(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        name="legacy-agent",
        version="4.1",
        digest="sha256:legacy-other",
        environment="staging",
    )
    _assert_deny(result, "VULNERABILITY_THRESHOLD_EXCEEDED")


def test_matching_unexpired_security_exception_is_allowed(runtime: Runtime) -> None:
    _, result = _invoke(
        runtime,
        name="legacy-agent",
        version="4.1",
        digest="sha256:legacy-valid",
        environment="staging",
    )
    _assert_allow(result, "EXCEPTION_ALLOW")
    assert result["exception_id"] == "SEC-100"
    assert result["cache_hit"] is False


def test_valid_signed_permit_verifies(runtime: Runtime) -> None:
    _, decision = _invoke(runtime)
    _assert_allow(decision)
    completed, result = _verify(runtime, decision["permit"])
    assert completed.returncode == 0
    assert result == {"valid": True}


def test_permit_payload_tamper_is_rejected(runtime: Runtime) -> None:
    _, decision = _invoke(runtime, instance="i-builder-001")
    token = decision["permit"]
    tampered = token.replace("i-builder-001", "i-builder-999")
    completed, result = _verify(runtime, tampered, instance="i-builder-999")
    assert completed.returncode == 43
    assert result == {"valid": False}


def test_permit_cannot_be_replayed_for_another_instance(runtime: Runtime) -> None:
    _, decision = _invoke(runtime, instance="i-builder-001")
    completed, result = _verify(runtime, decision["permit"], instance="i-builder-002")
    assert completed.returncode == 43
    assert result == {"valid": False}


def test_expired_permit_is_rejected(runtime: Runtime) -> None:
    _, decision = _invoke(runtime)
    completed, result = _verify(runtime, decision["permit"], now=NOW + 301)
    assert completed.returncode == 43
    assert result == {"valid": False}


def test_permit_is_bound_to_policy_generation(runtime: Runtime) -> None:
    _, decision = _invoke(runtime)
    _set_config(runtime.config, "policy_version", "policy-8")
    completed, result = _verify(runtime, decision["permit"])
    assert completed.returncode == 43
    assert result == {"valid": False}


def test_audit_journal_persists_allow_deny_and_exception_across_processes(runtime: Runtime) -> None:
    _, allowed = _invoke(runtime, instance="i-builder-a")
    _assert_allow(allowed)
    _, denied = _invoke(
        runtime,
        digest="sha256:pkg-vuln",
        instance="i-builder-b",
        now=NOW + 1,
    )
    _assert_deny(denied, "VULNERABILITY_THRESHOLD_EXCEEDED")
    _, excepted = _invoke(
        runtime,
        name="legacy-agent",
        version="4.1",
        digest="sha256:legacy-valid",
        environment="staging",
        instance="i-builder-c",
        now=NOW + 2,
    )
    _assert_allow(excepted, "EXCEPTION_ALLOW")

    audit_path = runtime.state / "audit.jsonl"
    assert audit_path.is_file()
    events = [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
    assert len(events) == 3
    assert [event["decision"] for event in events] == ["ALLOW", "DENY", "ALLOW"]
    assert events[1]["reason"] == "VULNERABILITY_THRESHOLD_EXCEEDED"
    assert events[2]["exception_id"] == "SEC-100"
    assert {event["instance"] for event in events} == {
        "i-builder-a",
        "i-builder-b",
        "i-builder-c",
    }
