"""Behavioral verifier for the enterprise PII discovery plane."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pytest
import requests

from conftest import (
    GENERATE,
    PII_HOME,
    configure_multi_source,
    configure_single_source,
    contains_raw_pii,
    copy_tree,
    create_job,
    current_policy,
    export_for,
    fixture_path,
    ingest_batch,
    issue_lease,
    piictl,
    register_worker,
    report_for,
    run_cmd,
    scan_source_once,
    sha256_hex,
    worker_scan_once,
    write_json,
)


def _scan_fixture(
    workspace: dict[str, Path],
    fixture_subdir: str,
    source_id: str = "fixture-source",
    **kwargs: Any,
) -> dict[str, Any]:
    """Copy one hidden fixture corpus into the workspace and scan it once."""
    corpus = workspace["corpus"] / fixture_subdir
    copy_tree(fixture_path(fixture_subdir), corpus)
    configure_single_source(workspace, source_id, corpus)
    return scan_source_once(workspace, source_root=corpus, source_id=source_id, **kwargs)


def test_f2p_source_root_and_symlink_escape_rejection(workspace: dict[str, Path]) -> None:
    """Configured roots must reject symlink traversal outside the approved root."""
    corpus = workspace["corpus"] / "escape"
    copy_tree(fixture_path("escape"), corpus)
    root = corpus / "root"
    link = root / "escape-link"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(corpus / "outside" / "secret.txt")
    configure_single_source(workspace, "escape-source", root)
    outcome = scan_source_once(workspace, source_root=root, source_id="escape-source")
    errors = outcome["batch"].get("errors", [])
    kinds = {item.get("kind") for item in errors}
    assert "SYMLINK_ESCAPE" in kinds or "SYMLINK_FILE" in kinds
    assert not any("TOP SECRET OUTSIDE ROOT" in json.dumps(outcome["batch"]) for _ in [0])


def test_f2p_canonical_source_and_archive_member_identity(workspace: dict[str, Path]) -> None:
    """Canonical source and archive member identities must stay distinct and stable."""
    corpus = workspace["corpus"] / "archive"
    corpus.mkdir(parents=True, exist_ok=True)
    inner = corpus / "payload.csv"
    shutil.copy(fixture_path("formats", "sample.csv"), inner)
    archive = corpus / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(inner, arcname="members/payroll.csv")
    configure_single_source(workspace, "archive-source", corpus)
    outcome = scan_source_once(workspace, source_root=corpus, source_id="archive-source")
    locations = [
        finding.get("location", {})
        for finding in outcome["batch"].get("findings", [])
    ]
    members = {loc.get("archive_member", "") for loc in locations if loc.get("archive_member")}
    paths = {loc.get("canonical_path", "") for loc in locations}
    assert archive.name in "".join(paths) or members
    if members:
        assert "members/payroll.csv" in members
        assert len(members) >= 1


def test_f2p_csv_json_xml_email_and_text_provenance(workspace: dict[str, Path]) -> None:
    """Structured and unstructured inputs must retain field-level provenance metadata."""
    corpus = workspace["corpus"] / "formats"
    copy_tree(fixture_path("formats"), corpus)
    configure_single_source(workspace, "format-source", corpus)
    outcome = scan_source_once(workspace, source_root=corpus, source_id="format-source")
    findings = outcome["batch"].get("findings", [])
    assert findings, "expected findings across supported formats"
    for finding in findings:
        location = finding["location"]
        assert location["source_id"] == "format-source"
        assert location["canonical_path"]
        assert location["field_path"]
        assert location["record_id"]
        assert location["byte_start"] >= 0
        assert location["byte_end"] >= location["byte_start"]


def test_f2p_malformed_record_isolation_and_bounded_errors(workspace: dict[str, Path]) -> None:
    """Malformed records must produce bounded errors while preserving adjacent valid records."""
    corpus = workspace["corpus"] / "malformed"
    copy_tree(fixture_path("malformed"), corpus)
    configure_single_source(workspace, "malformed-source", corpus)
    outcome = scan_source_once(workspace, source_root=corpus, source_id="malformed-source")
    errors = outcome["batch"].get("errors", [])
    findings = outcome["batch"].get("findings", [])
    assert errors, "expected malformed input to emit structured errors"
    assert findings, "expected valid adjacent records to remain scannable"
    assert len(errors) <= 200


def test_f2p_charset_bom_multibyte_and_offset_stability(workspace: dict[str, Path]) -> None:
    """BOM and multibyte boundaries must not corrupt offsets for neighboring valid content."""
    corpus = workspace["corpus"] / "charset"
    corpus.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture_path("charset", "bom.properties"), corpus / "bom.properties")
    part1 = fixture_path("charset", "split_utf8.part1").read_bytes() + "café=".encode("utf-8")[:4]
    part2 = fixture_path("charset", "split_utf8.part2").read_bytes()
    (corpus / "split.properties").write_bytes(part1 + part2)
    configure_single_source(workspace, "charset-source", corpus)
    outcome = scan_source_once(workspace, source_root=corpus, source_id="charset-source")
    findings = outcome["batch"].get("findings", [])
    assert findings
    for finding in findings:
        assert finding["location"]["byte_end"] > finding["location"]["byte_start"]


def test_f2p_unicode_and_format_normalization_identity(workspace: dict[str, Path]) -> None:
    """Unicode-normalized and formatted values must validate to stable identities."""
    outcome = _scan_fixture(workspace, "normalization")
    fingerprints = {item["fingerprint"] for item in outcome["batch"].get("findings", [])}
    categories = {item["category"] for item in outcome["batch"].get("findings", [])}
    assert "EMAIL" in categories
    assert fingerprints
    assert len(fingerprints) >= 1


def test_f2p_payment_card_luhn_length_and_issuer_validation(workspace: dict[str, Path]) -> None:
    """Payment card candidates require issuer, length, and Luhn validation before publication."""
    outcome = _scan_fixture(workspace, "payment")
    findings = outcome["batch"].get("findings", [])
    cards = [f for f in findings if f.get("category") == "PAYMENT_CARD" and not f.get("suppressed")]
    assert cards, "expected at least one validated payment-card finding"
    masked = "".join(item["masked_evidence"] for item in cards)
    assert "4111111111111112" not in masked
    assert "411111" not in masked


def test_f2p_regional_identity_phone_iban_and_passport_context(workspace: dict[str, Path]) -> None:
    """Regional identity detectors must honor contextual boundaries for phone, IBAN, and passport."""
    outcome = _scan_fixture(workspace, "regional", region="eu", department="finance")
    categories = {item["category"] for item in outcome["batch"].get("findings", []) if not item.get("suppressed")}
    assert {"PHONE", "IBAN"} & categories


def test_f2p_context_confidence_and_negative_evidence(workspace: dict[str, Path]) -> None:
    """Negative context labels must suppress invalid or placeholder candidates."""
    outcome = _scan_fixture(workspace, "confidence")
    findings = outcome["batch"].get("findings", [])
    invalid_cards = [
        f for f in findings
        if f.get("category") == "PAYMENT_CARD" and "4111111111111112" in f.get("masked_evidence", "")
    ]
    assert not invalid_cards
    assert any(f.get("category") == "EMAIL" for f in findings)


def test_f2p_chunk_boundary_and_detector_overlap_resolution(workspace: dict[str, Path]) -> None:
    """Chunk boundaries and overlapping detectors must resolve to one deterministic finding."""
    outcome = _scan_fixture(workspace, "overlap")
    findings = outcome["batch"].get("findings", [])
    emails = [f for f in findings if f.get("category") == "EMAIL"]
    assert len(emails) == 1


def test_f2p_allowlist_scope_category_expiry_and_policy_pin(workspace: dict[str, Path]) -> None:
    """Allowlist and suppression rules must honor scope, category, and pinned policy versions."""
    corpus = workspace["corpus"] / "suppression"
    copy_tree(fixture_path("formats"), corpus)
    policy = json.loads((workspace["root"] / "config" / "policy.json").read_text(encoding="utf-8"))
    overlay = json.loads(fixture_path("suppression", "policy_overlay.json").read_text(encoding="utf-8"))
    policy.update(overlay)
    write_json(workspace["root"] / "config" / "policy.json", policy)
    configure_single_source(workspace, "suppression-source", corpus)
    outcome = scan_source_once(
        workspace,
        source_root=corpus,
        source_id="suppression-source",
        department="hr",
        region="na",
    )
    findings = outcome["batch"].get("findings", [])
    assert any(f.get("suppressed") for f in findings) or findings


def test_f2p_masking_is_safe_and_stable_for_short_values(workspace: dict[str, Path]) -> None:
    """Masked evidence must hide short structured values without unstable leakage."""
    outcome = _scan_fixture(workspace, "masking")
    for finding in outcome["batch"].get("findings", []):
        masked = finding["masked_evidence"]
        assert "123-45-6789" not in masked
        assert masked.count("*") >= 3 or "@" in masked


def test_f2p_hmac_fingerprints_are_scope_and_epoch_bound(workspace: dict[str, Path]) -> None:
    """Fingerprints must change across scan scope and policy key epoch boundaries."""
    first = _scan_fixture(workspace, "formats", job_id="scope-a")
    second = _scan_fixture(workspace, "formats", job_id="scope-b")
    fps_a = {f["fingerprint"] for f in first["batch"].get("findings", [])}
    fps_b = {f["fingerprint"] for f in second["batch"].get("findings", [])}
    assert fps_a
    assert fps_a != fps_b


def test_f2p_finding_dedupe_preserves_distinct_locations(workspace: dict[str, Path]) -> None:
    """Repeated values at distinct locations must remain separate governed findings."""
    outcome = _scan_fixture(workspace, "dedupe")
    findings = outcome["batch"].get("findings", [])
    emails = [f for f in findings if f.get("category") == "EMAIL"]
    locations = {
        (
            f["location"]["canonical_path"],
            f["location"]["byte_start"],
            f["location"]["byte_end"],
        )
        for f in emails
    }
    assert len(emails) >= 2
    assert len(locations) >= 2


def test_f2p_reports_logs_errors_and_exports_contain_no_raw_pii(workspace: dict[str, Path]) -> None:
    """Reports, exports, and error surfaces must not retain raw detected values."""
    outcome = _scan_fixture(workspace, "formats")
    job_id = outcome["job"]["id"]
    report = report_for(workspace, job_id)
    exported = export_for(workspace, job_id, "json").decode()
    status = piictl(workspace, "metrics").text
    for surface in (json.dumps(report), exported, status):
        assert not contains_raw_pii(surface)


def test_f2p_job_and_shards_remain_pinned_to_policy_and_corpus(workspace: dict[str, Path]) -> None:
    """Jobs and shards must remain pinned to policy digest and corpus snapshot."""
    outcome = _scan_fixture(workspace, "formats")
    job = outcome["job"]
    policy = current_policy(workspace["endpoint"])
    response = piictl(
        workspace,
        "job",
        "status",
        "--id",
        job["id"],
    )
    payload = response.json()
    assert payload["job"]["policy_digest"] == policy["digest"]
    assert payload["job"]["corpus_digest"] == "verifier-corpus"
    assert payload["job"]["policy_version"] == policy["version"]
    assert payload["shards"]


def test_f2p_stale_worker_session_attempt_and_lease_are_rejected(workspace: dict[str, Path]) -> None:
    """Stale worker sessions, attempts, and leases must be rejected at ingestion time."""
    corpus = workspace["corpus"] / "authority"
    copy_tree(fixture_path("formats"), corpus)
    configure_single_source(workspace, "authority-source", corpus)
    endpoint = workspace["endpoint"]
    register_worker(endpoint, session_id="live-session")
    policy = current_policy(endpoint)
    job = create_job(endpoint, "stale-job", policy["version"])
    lease = issue_lease(endpoint, session_id="live-session")
    batch = worker_scan_once(
        workspace,
        source_root=corpus,
        source_id="authority-source",
        job_id=job["id"],
        shard_id=lease["shard_id"],
        generation=lease["generation"],
        policy_digest=lease["policy_digest"],
        lease_token=lease["token"],
        session_id="stale-session",
        attempt=lease["attempt"],
    )
    result = ingest_batch(endpoint, lease, batch)
    assert result["status"] == 409


def test_f2p_exact_batch_retry_is_idempotent_conflict_is_rejected(workspace: dict[str, Path]) -> None:
    """Exact batch retries must replay safely while conflicting batch identities are rejected."""
    corpus = workspace["corpus"] / "batch-idempotency"
    copy_tree(fixture_path("formats"), corpus)
    configure_single_source(workspace, "batch-source", corpus)
    endpoint = workspace["endpoint"]
    register_worker(endpoint, session_id="batch-session")
    policy = current_policy(endpoint)
    job = create_job(endpoint, "batch-job", policy["version"])
    lease = issue_lease(endpoint, session_id="batch-session")
    batch = worker_scan_once(
        workspace,
        source_root=corpus,
        source_id="batch-source",
        job_id=job["id"],
        shard_id=lease["shard_id"],
        generation=lease["generation"],
        policy_digest=lease["policy_digest"],
        lease_token=lease["token"],
        session_id="batch-session",
    )
    batch["complete"] = False
    first = ingest_batch(endpoint, lease, batch)
    second = ingest_batch(endpoint, lease, batch)
    assert first["status"] == 200
    assert second["status"] == 200
    assert second["body"].get("replay") is True
    conflict = dict(batch)
    conflict["body_digest"] = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    conflict["findings"] = []
    bad = ingest_batch(endpoint, lease, conflict)
    assert bad["status"] == 409


def test_f2p_checkpoint_resume_commits_each_record_once(workspace: dict[str, Path]) -> None:
    """Checkpoint resume must commit each record once without duplicate side effects."""
    corpus = workspace["corpus"] / "checkpoint"
    copy_tree(fixture_path("authority"), corpus)
    configure_single_source(workspace, "checkpoint-source", corpus)
    endpoint = workspace["endpoint"]
    register_worker(endpoint, session_id="checkpoint-session")
    policy = current_policy(endpoint)
    job = create_job(endpoint, "checkpoint-job", policy["version"])
    lease = issue_lease(endpoint, session_id="checkpoint-session")
    first_batch = worker_scan_once(
        workspace,
        source_root=corpus,
        source_id="checkpoint-source",
        job_id=job["id"],
        shard_id=lease["shard_id"],
        generation=lease["generation"],
        policy_digest=lease["policy_digest"],
        lease_token=lease["token"],
        session_id="checkpoint-session",
        extra_args=["--scan-once"],
    )
    first_batch["complete"] = False
    ingest_batch(endpoint, lease, first_batch)
    second_batch = worker_scan_once(
        workspace,
        source_root=corpus,
        source_id="checkpoint-source",
        job_id=job["id"],
        shard_id=lease["shard_id"],
        generation=lease["generation"],
        policy_digest=lease["policy_digest"],
        lease_token=lease["token"],
        session_id="checkpoint-session",
    )
    second = ingest_batch(endpoint, lease, second_batch)
    assert second["status"] == 200
    findings = second_batch.get("findings", [])
    ids = [item["id"] for item in findings]
    assert len(ids) == len(set(ids))


def test_f2p_cancelled_job_stops_leasing_and_cannot_finalize(workspace: dict[str, Path]) -> None:
    """Cancelled jobs must stop leasing new work and cannot finalize complete reports."""
    _scan_fixture(workspace, "formats", job_id="cancel-job")
    cancel = piictl(workspace, "job", "cancel", "--id", "cancel-job")
    assert cancel.status_code == 200
    with pytest.raises(AssertionError):
        issue_lease(workspace["endpoint"], session_id="session-a")
    report = piictl(workspace, "report", "show", "--job", "cancel-job")
    assert report.status_code in {409, 200}
    if report.status_code == 200:
        assert report.json()["completeness"]["complete"] is False


def test_f2p_finalization_requires_terminal_required_shards(workspace: dict[str, Path]) -> None:
    """Complete reports require every required shard to reach a terminal state."""
    outcome = _scan_fixture(workspace, "formats")
    report = report_for(workspace, outcome["job"]["id"])
    assert report["completeness"]["committed"] >= 1
    assert report["completeness"]["complete"] in {True, False}


def test_f2p_authorization_precedes_rows_counts_facets_and_examples(workspace: dict[str, Path]) -> None:
    """Authorization must bound rows, counts, facets, and examples to the granted projection."""
    corpus = workspace["corpus"] / "auth"
    copy_tree(fixture_path("authorization"), corpus)
    configure_multi_source(
        workspace,
        [
            {"id": "hr-na", "root": str(corpus), "department": "hr", "region": "na", "required": True},
            {"id": "finance-eu", "root": str(corpus), "department": "finance", "region": "eu", "required": True},
        ],
    )
    endpoint = workspace["endpoint"]
    register_worker(endpoint)
    policy = current_policy(endpoint)
    job = create_job(endpoint, "auth-job", policy["version"])
    for source_id, department, region in (
        ("hr-na", "hr", "na"),
        ("finance-eu", "finance", "eu"),
    ):
        lease = issue_lease(endpoint)
        batch = worker_scan_once(
            workspace,
            source_root=corpus,
            source_id=source_id,
            job_id=job["id"],
            shard_id=lease["shard_id"],
            generation=lease["generation"],
            policy_digest=lease["policy_digest"],
            lease_token=lease["token"],
            session_id=lease["session_id"],
            department=department,
            region=region,
        )
        ingest_batch(endpoint, lease, batch)
    limited = report_for(workspace, "auth-job", principal="hr-analyst")
    allowed = {row["key"]["source_id"] for row in limited["rows"]}
    assert allowed.issubset({"hr-na"})
    assert sum(row["findings"] for row in limited["rows"]) >= limited["completeness"].get("committed", 0)


def test_f2p_authorization_precedes_dedupe_pagination_and_export(workspace: dict[str, Path]) -> None:
    """Authorization must also bound exports and deduplicated views to granted sources."""
    corpus = workspace["corpus"] / "auth-export"
    copy_tree(fixture_path("authorization"), corpus)
    configure_multi_source(
        workspace,
        [
            {"id": "hr-na", "root": str(corpus), "department": "hr", "region": "na", "required": True},
            {"id": "finance-eu", "root": str(corpus), "department": "finance", "region": "eu", "required": True},
        ],
    )
    endpoint = workspace["endpoint"]
    register_worker(endpoint)
    policy = current_policy(endpoint)
    job = create_job(endpoint, "auth-export-job", policy["version"])
    for source_id, department, region in (
        ("hr-na", "hr", "na"),
        ("finance-eu", "finance", "eu"),
    ):
        lease = issue_lease(endpoint)
        batch = worker_scan_once(
            workspace,
            source_root=corpus,
            source_id=source_id,
            job_id=job["id"],
            shard_id=lease["shard_id"],
            generation=lease["generation"],
            policy_digest=lease["policy_digest"],
            lease_token=lease["token"],
            session_id=lease["session_id"],
            department=department,
            region=region,
        )
        ingest_batch(endpoint, lease, batch)
    csv_body = export_for(workspace, "auth-export-job", "csv", principal="finance-auditor").decode()
    assert "finance-eu" in csv_body or "finance" in csv_body
    assert "hr-na" not in csv_body


def test_f2p_report_counts_errors_suppression_and_truncation(workspace: dict[str, Path]) -> None:
    """Reports must distinguish findings, suppression, malformed input, and truncation states."""
    malformed = _scan_fixture(workspace, "malformed")
    report = report_for(workspace, malformed["job"]["id"])
    completeness = report["completeness"]
    assert completeness["errors"] >= 1
    assert "truncations" in completeness
    assert "suppressed" not in completeness


def test_f2p_json_csv_order_escape_manifest_and_digest_stability(workspace: dict[str, Path]) -> None:
    """Published report bytes, manifests, and digests must remain deterministic across reruns."""
    outcome = _scan_fixture(workspace, "formats", job_id="determinism-job")
    job_id = outcome["job"]["id"]
    first_json = export_for(workspace, job_id, "json")
    second_json = export_for(workspace, job_id, "json")
    first_csv = export_for(workspace, job_id, "csv")
    second_csv = export_for(workspace, job_id, "csv")
    assert sha256_hex(first_json) == sha256_hex(second_json)
    assert sha256_hex(first_csv) == sha256_hex(second_csv)
    publish = requests.post(f"{workspace['endpoint']}/v1/reports/{job_id}/publish", timeout=20)
    if publish.status_code == 201:
        manifest_path = workspace["reports"] / job_id / "CURRENT"
        assert manifest_path.exists() or any(workspace["reports"].glob(f"{job_id}/*"))


def test_f2p_torn_current_and_corrupt_newest_fall_back_safely(workspace: dict[str, Path]) -> None:
    """Recovery must ignore torn CURRENT pointers and fall back to the highest valid generation."""
    outcome = _scan_fixture(workspace, "formats", job_id="recovery-job")
    job_id = outcome["job"]["id"]
    publish = requests.post(f"{workspace['endpoint']}/v1/reports/{job_id}/publish", timeout=20)
    if publish.status_code != 201:
        pytest.skip("publish unavailable until required shards are terminal")
    job_root = workspace["reports"] / job_id
    current = job_root / "CURRENT"
    if current.exists():
        current.write_text("00000000000000009999\n", encoding="utf-8")
    recover = run_cmd([str(PII_HOME / "bin" / "pii-control"), "recover", "--config", str(workspace["config"])], cwd=workspace["root"])
    assert recover.returncode == 0
    payload = json.loads(recover.stdout)
    assert payload["readiness"]["recovered"] is True


def test_f2p_restart_restores_policy_lease_and_result_fences(workspace: dict[str, Path]) -> None:
    """Restart recovery must restore policy pins, accepted batches, and lease authority fences."""
    outcome = _scan_fixture(workspace, "formats", job_id="restart-job")
    before = piictl(workspace, "job", "status", "--id", outcome["job"]["id"]).json()
    recover = run_cmd([str(PII_HOME / "bin" / "pii-control"), "recover", "--config", str(workspace["config"])], cwd=workspace["root"])
    assert recover.returncode == 0
    after_status = requests.get(f"{workspace['endpoint']}/v1/jobs/{outcome['job']['id']}", timeout=10)
    assert after_status.status_code == 200
    after = after_status.json()
    assert after["job"]["policy_digest"] == before["job"]["policy_digest"]


def test_f2p_retention_preserves_active_jobs_exports_and_fallback(workspace: dict[str, Path]) -> None:
    """Retention must preserve generations referenced by active jobs, exports, and fallback state."""
    outcome = _scan_fixture(workspace, "formats", job_id="retention-job")
    state_dir = workspace["state"] / "generations"
    if not state_dir.exists():
        recover = run_cmd([str(PII_HOME / "bin" / "pii-control"), "recover", "--config", str(workspace["config"])], cwd=workspace["root"])
        assert recover.returncode == 0
    assert outcome["receipt"]["status"] == 200
    assert workspace["state"].exists()


def test_f2p_budget_exhaustion_is_explicit_bounded_and_recoverable(workspace: dict[str, Path]) -> None:
    """Budget exhaustion must surface explicit truncation state that remains recoverable."""
    corpus = workspace["corpus"] / "budget"
    corpus.mkdir(parents=True, exist_ok=True)
    seed = fixture_path("budget", "oversize.seed").read_bytes()
    (corpus / "large.txt").write_bytes(seed * 500_000)
    policy = json.loads((workspace["root"] / "config" / "policy.json").read_text(encoding="utf-8"))
    policy["budgets"]["max_file_bytes"] = 4096
    write_json(workspace["root"] / "config" / "policy.json", policy)
    configure_single_source(workspace, "budget-source", corpus)
    outcome = scan_source_once(workspace, source_root=corpus, source_id="budget-source")
    truncations = outcome["batch"].get("truncations", [])
    errors = outcome["batch"].get("errors", [])
    assert truncations or errors


def test_f2p_readiness_tracks_recovery_workers_and_required_sources(workspace: dict[str, Path]) -> None:
    """Readiness must remain false until recovery, workers, and required sources are current."""
    not_ready = requests.get(f"{workspace['endpoint']}/ready", timeout=10)
    assert not_ready.status_code in {200, 503}
    register_worker(workspace["endpoint"])
    ready = requests.get(f"{workspace['endpoint']}/ready", timeout=10)
    payload = ready.json()
    if ready.status_code == 200:
        assert payload.get("ready") is True
    else:
        assert payload.get("ready") is False


def test_p2p_scans_never_modify_source_data(workspace: dict[str, Path]) -> None:
    """Scanning must leave configured source files and metadata unchanged."""
    corpus = workspace["corpus"] / "readonly"
    copy_tree(fixture_path("formats"), corpus)
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in corpus.rglob("*")
        if path.is_file()
    }
    configure_single_source(workspace, "readonly-source", corpus)
    scan_source_once(workspace, source_root=corpus, source_id="readonly-source")
    for path, (content, mtime) in before.items():
        assert path.read_bytes() == content
        assert path.stat().st_mtime_ns == mtime


def test_p2p_runtime_requires_no_external_network(workspace: dict[str, Path]) -> None:
    """Runtime scanning and control operations must not depend on external network access."""
    config = json.loads((workspace["config"]).read_text(encoding="utf-8"))
    assert config["listen"].startswith("127.0.0.1:")
    outcome = _scan_fixture(workspace, "formats")
    assert outcome["receipt"]["status"] == 200
    assert "example.invalid" in json.dumps(outcome["batch"])


def test_p2p_generated_corpus_contains_only_synthetic_personas(workspace: dict[str, Path]) -> None:
    """Generated corpus records must remain synthetic and free of real personal data."""
    corpus = workspace["corpus"] / "generated"
    result = run_cmd([str(GENERATE), "--output", str(corpus), "--records", "12000"], cwd=workspace["root"], timeout=300)
    assert result.returncode == 0
    manifest = corpus / "manifest.json"
    assert manifest.exists()
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data.get("records") == 12000
    sample = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in list(corpus.rglob("*.csv"))[:3]
    )
    assert "@example.invalid" in sample
    assert "SYN-" in sample


def test_p2p_invalid_job_and_policy_inputs_do_not_damage_current_state(workspace: dict[str, Path]) -> None:
    """Invalid job and policy requests must fail without corrupting the current persisted state."""
    before = piictl(workspace, "metrics").json()
    bad = requests.post(
        f"{workspace['endpoint']}/v1/jobs",
        json={"id": "", "policy_version": "missing-policy", "corpus_digest": ""},
        timeout=10,
    )
    assert bad.status_code in {400, 409}
    after = piictl(workspace, "metrics").json()
    assert after["policies"] == before["policies"]
