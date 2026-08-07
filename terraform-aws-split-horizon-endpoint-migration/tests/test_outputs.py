"""Verifier for split-horizon VPC endpoint migration.

Replans the submitted Terraform module, plans the consumer root, plans
against a legacy state fixture, and runs the trusted DNS/reachability lab.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))
import endpoint_lab  # noqa: E402

TERRAFORM_ARTIFACT = Path("/app/terraform")
VAR_ARTIFACT = Path("/app/var/endpoint")
OUTPUT_ARTIFACT = Path("/app/output")
BASE_DATA = FIXTURES / "data"
VERIFIER_DATA = Path("/app/data")

ENV = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
    "TF_IN_AUTOMATION": "1",
    "CHECKPOINT_DISABLE": "1",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
    "ENDPOINT_DATA_DIR": str(VERIFIER_DATA),
    "ENDPOINT_VAR_DIR": "/tmp/endpoint-var",
    "ENDPOINT_OUTPUT_DIR": "/tmp/endpoint-output",
}

os.environ.update(
    {
        "ENDPOINT_DATA_DIR": str(VERIFIER_DATA),
        "ENDPOINT_VAR_DIR": "/tmp/endpoint-var",
        "ENDPOINT_OUTPUT_DIR": "/tmp/endpoint-output",
    }
)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), env=ENV, text=True, capture_output=True)


def _reset_data(overrides: dict[str, object] | None = None) -> None:
    if VERIFIER_DATA.exists():
        shutil.rmtree(VERIFIER_DATA)
    shutil.copytree(BASE_DATA, VERIFIER_DATA)
    if overrides:
        for name, content in overrides.items():
            (VERIFIER_DATA / name).write_text(
                json.dumps(content, indent=2) + "\n", encoding="utf-8"
            )


def _load_base(name: str) -> object:
    return json.loads((BASE_DATA / name).read_text(encoding="utf-8"))


def _fresh_copy(dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        TERRAFORM_ARTIFACT,
        dest,
        ignore=shutil.ignore_patterns(
            ".terraform", ".terraform.lock.hcl", "*.tfstate*", "tfplan", "*.tfplan"
        ),
    )
    return dest


def _plan(workspace: Path, state: Path | None = None) -> subprocess.CompletedProcess:
    init = _run(["terraform", "init", "-backend=false", "-input=false"], workspace)
    if init.returncode != 0:
        return init
    cmd = ["terraform", "plan", "-refresh=false", "-input=false", "-out=tfplan", "-no-color"]
    if state is not None:
        cmd.insert(-2, f"-state={state}")
    return _run(cmd, workspace)


def _show(workspace: Path) -> dict:
    proc = _run(["terraform", "show", "-json", "tfplan"], workspace)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def _replan(workspace: Path, state: Path | None = None) -> tuple[dict | None, subprocess.CompletedProcess]:
    proc = _plan(workspace, state=state)
    if proc.returncode != 0:
        return None, proc
    return _show(workspace), proc


def _evidence_from(staging: dict, consumer: dict, legacy: dict) -> dict:
    graph = endpoint_lab.normalize_plan(staging)
    dns = endpoint_lab.run_dns_probes(graph)
    reach = endpoint_lab.run_reachability_probes(graph)
    safe = endpoint_lab.migration_is_safe(legacy)
    # Do not write agent paths; compute digest like write_evidence
    graph_errors = endpoint_lab.validate_graph(graph)
    all_probes = dns + reach
    ready = safe and not graph_errors and all(p.get("ok") for p in all_probes)
    status = "READY" if ready else "FAILED"
    stable = {
        "status": status,
        "plan_digest": endpoint_lab.plan_digest(staging),
        "consumer_plan_digest": endpoint_lab.plan_digest(consumer),
        "migration_safe": safe,
        "dns_probes": dns,
        "reachability_probes": reach,
    }
    digest = hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**stable, "graph_errors": graph_errors, "evidence_digest": digest}


@pytest.fixture(autouse=True)
def _clean_data():
    _reset_data()
    for path in (Path("/tmp/endpoint-var"), Path("/tmp/endpoint-output")):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    yield
    _reset_data()


@pytest.fixture(scope="session")
def submission_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _fresh_copy(tmp_path_factory.mktemp("submission") / "terraform")


@pytest.fixture(scope="session")
def agent_evidence() -> dict:
    path = OUTPUT_ARTIFACT / "migration-evidence.json"
    assert path.is_file(), "missing /app/output/migration-evidence.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def baseline(submission_dir: Path) -> tuple[dict, dict, dict, dict]:
    """Independent staging + consumer + legacy plans and lab evidence."""
    _reset_data()
    staging_ws = submission_dir / "workspaces" / "staging"
    consumer_ws = submission_dir / "workspaces" / "consumer"
    staging, proc = _replan(staging_ws)
    assert staging is not None, proc.stdout + proc.stderr
    consumer, proc = _replan(consumer_ws)
    assert consumer is not None, proc.stdout + proc.stderr
    legacy_state = VERIFIER_DATA / "legacy_state.json"
    legacy, proc = _replan(staging_ws, state=legacy_state)
    assert legacy is not None, proc.stdout + proc.stderr
    evidence = _evidence_from(staging, consumer, legacy)
    return staging, consumer, legacy, evidence


def test_agent_artifacts_exist_and_parse(agent_evidence: dict) -> None:
    """Agent must leave a regenerated plan and READY migration evidence."""
    plan_path = VAR_ARTIFACT / "plan.json"
    assert plan_path.is_file(), "missing /app/var/endpoint/plan.json"
    json.loads(plan_path.read_text(encoding="utf-8"))
    assert agent_evidence.get("status") == "READY"
    assert agent_evidence.get("evidence_digest")
    assert agent_evidence.get("migration_safe") is True
    failing = [
        p["name"]
        for p in (agent_evidence.get("dns_probes") or [])
        + (agent_evidence.get("reachability_probes") or [])
        if not p.get("ok")
    ]
    assert not failing, failing


def test_baseline_lab_ready(baseline: tuple[dict, dict, dict, dict]) -> None:
    """Trusted lab must accept the submitted plan on baseline inventory."""
    _s, _c, _l, evidence = baseline
    assert evidence["status"] == "READY", evidence.get("graph_errors")
    assert evidence["migration_safe"] is True


def test_gateway_and_interface_semantics(baseline: tuple[dict, dict, dict, dict]) -> None:
    """Gateway endpoints cover only private RTs; interface endpoints stay private."""
    staging, _c, _l, _e = baseline
    graph = endpoint_lab.normalize_plan(staging)
    errors = endpoint_lab.validate_graph(graph)
    assert not errors, errors
    for svc in graph["endpoints_catalog"]["gateway"]:
        assert set(graph["gw_coverage"][svc]) == set(graph["private_rt_keys"])
    for svc in graph["endpoints_catalog"]["interface"]:
        assert set(graph["if_placement"][svc]) == set(graph["private_subnet_keys"])
        assert graph["interface_eps"][svc]["private_dns_enabled"] is True


def test_split_horizon_dns_probes(baseline: tuple[dict, dict, dict, dict]) -> None:
    """Private view resolves SSM names; public view must not inherit them."""
    _s, _c, _l, evidence = baseline
    by_name = {p["name"]: p for p in evidence["dns_probes"]}
    assert by_name["private-dns:ssm"]["ok"] is True
    assert by_name["public-isolation:ssm"]["ok"] is True
    assert by_name["overlap-private-owner"]["ok"] is True
    assert by_name["overlap-public-not-private"]["ok"] is True


def test_consumer_plan_succeeds(baseline: tuple[dict, dict, dict, dict]) -> None:
    """Downstream consumer root must plan using legacy and aggregate outputs."""
    _s, consumer, _l, evidence = baseline
    outputs = ((consumer.get("planned_values") or {}).get("outputs") or {})
    assert "consumer_ok" in outputs
    assert evidence["consumer_plan_digest"]


def test_legacy_migration_non_destructive(baseline: tuple[dict, dict, dict, dict]) -> None:
    """Planning against legacy list-indexed state must not delete preserved identities."""
    _s, _c, legacy, evidence = baseline
    assert endpoint_lab.migration_is_safe(legacy) is True
    assert evidence["migration_safe"] is True


def test_idempotent_evidence_digest(submission_dir: Path) -> None:
    """Two clean verifier runs against the same inputs share an evidence digest."""
    staging_ws = submission_dir / "workspaces" / "staging"
    consumer_ws = submission_dir / "workspaces" / "consumer"
    _reset_data()
    s1, p1 = _replan(staging_ws)
    assert s1 is not None, p1.stdout + p1.stderr
    c1, p1 = _replan(consumer_ws)
    assert c1 is not None, p1.stdout + p1.stderr
    legacy_state = VERIFIER_DATA / "legacy_state.json"
    l1, p1 = _replan(staging_ws, state=legacy_state)
    assert l1 is not None, p1.stdout + p1.stderr
    e1 = _evidence_from(s1, c1, l1)

    _reset_data()
    s2, p2 = _replan(staging_ws)
    assert s2 is not None, p2.stdout + p2.stderr
    c2, p2 = _replan(consumer_ws)
    assert c2 is not None, p2.stdout + p2.stderr
    l2, p2 = _replan(staging_ws, state=legacy_state)
    assert l2 is not None, p2.stdout + p2.stderr
    e2 = _evidence_from(s2, c2, l2)
    assert e1["status"] == "READY"
    assert e1["evidence_digest"] == e2["evidence_digest"]


def test_hidden_reorder_subnets_still_ready(submission_dir: Path) -> None:
    """Reordering subnet map keys must preserve private placement semantics."""
    inventory = copy.deepcopy(_load_base("inventory.json"))
    items = list(inventory["subnets"].items())
    inventory["subnets"] = dict(reversed(items))
    _reset_data(overrides={"inventory.json": inventory})
    staging_ws = submission_dir / "workspaces" / "staging"
    consumer_ws = submission_dir / "workspaces" / "consumer"
    staging, proc = _replan(staging_ws)
    assert staging is not None, proc.stdout + proc.stderr
    consumer, proc = _replan(consumer_ws)
    assert consumer is not None, proc.stdout + proc.stderr
    legacy, proc = _replan(staging_ws, state=VERIFIER_DATA / "legacy_state.json")
    assert legacy is not None, proc.stdout + proc.stderr
    evidence = _evidence_from(staging, consumer, legacy)
    assert evidence["status"] == "READY", evidence.get("graph_errors")


def test_hidden_added_interface_endpoint(submission_dir: Path) -> None:
    """Adding one valid interface endpoint must place it privately with DNS on."""
    endpoints = copy.deepcopy(_load_base("endpoints.json"))
    endpoints["interface"]["kms"] = {
        "service": "kms",
        "private_dns_name": "kms.us-east-1.amazonaws.com",
        "lab_ipv4": "10.42.16.13",
    }
    _reset_data(overrides={"endpoints.json": endpoints})
    staging_ws = submission_dir / "workspaces" / "staging"
    consumer_ws = submission_dir / "workspaces" / "consumer"
    staging, proc = _replan(staging_ws)
    assert staging is not None, proc.stdout + proc.stderr
    consumer, proc = _replan(consumer_ws)
    assert consumer is not None, proc.stdout + proc.stderr
    legacy, proc = _replan(staging_ws, state=VERIFIER_DATA / "legacy_state.json")
    assert legacy is not None, proc.stdout + proc.stderr
    evidence = _evidence_from(staging, consumer, legacy)
    assert evidence["status"] == "READY", evidence.get("graph_errors")
    graph = endpoint_lab.normalize_plan(staging)
    assert "kms" in graph["interface_eps"]
    assert set(graph["if_placement"]["kms"]) == set(graph["private_subnet_keys"])


def test_invalid_open_cidr_fails_graph(submission_dir: Path) -> None:
    """Allowed sources that include 0.0.0.0/0 must not reach READY."""
    allowed = copy.deepcopy(_load_base("allowed_sources.json"))
    allowed["cidr_blocks"] = ["0.0.0.0/0"]
    _reset_data(overrides={"allowed_sources.json": allowed})
    staging_ws = submission_dir / "workspaces" / "staging"
    consumer_ws = submission_dir / "workspaces" / "consumer"
    staging, proc = _replan(staging_ws)
    if staging is None:
        return
    consumer, proc = _replan(consumer_ws)
    if consumer is None:
        return
    legacy, proc = _replan(staging_ws, state=VERIFIER_DATA / "legacy_state.json")
    if legacy is None:
        return
    evidence = _evidence_from(staging, consumer, legacy)
    assert evidence["status"] == "FAILED"


def test_counterexample_public_gateway_attachment_fails(
    baseline: tuple[dict, dict, dict, dict],
) -> None:
    """Tampering the plan to attach a gateway endpoint to a public RT must fail."""
    staging, consumer, legacy, _e = baseline
    tampered = copy.deepcopy(staging)
    changes = tampered.setdefault("resource_changes", [])
    changes.append(
        {
            "address": 'module.network.aws_vpc_endpoint_route_table_association.gateway["s3:public-a"]',
            "type": "aws_vpc_endpoint_route_table_association",
            "change": {"actions": ["create"], "after": {}},
        }
    )
    evidence = _evidence_from(tampered, consumer, legacy)
    assert evidence["status"] == "FAILED"


def test_counterexample_missing_moved_is_unsafe(submission_dir: Path) -> None:
    """Without moved blocks, legacy private subnet addresses are destroyed."""
    staging_ws = submission_dir / "workspaces" / "staging"
    moved = staging_ws.parent.parent / "modules" / "network" / "moved.tf"
    backup = moved.read_text(encoding="utf-8") if moved.is_file() else ""
    try:
        if moved.is_file():
            moved.write_text("# cleared for counterexample\n", encoding="utf-8")
        staging, proc = _replan(staging_ws)
        assert staging is not None, proc.stdout + proc.stderr
        legacy, proc = _replan(staging_ws, state=VERIFIER_DATA / "legacy_state.json")
        assert legacy is not None, proc.stdout + proc.stderr
        assert endpoint_lab.migration_is_safe(legacy) is False
    finally:
        if moved.is_file():
            moved.write_text(backup, encoding="utf-8")
