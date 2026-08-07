"""Verifier for the claims edge exception cutover.

Rebuilds the submitted Terraform module/workspace in an isolated verifier
copy, replays it through the trusted local edge lab, and checks the
cutover evidence the agent produced in its own environment against an
independently derived plan and probe run.
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
import edge_lab  # noqa: E402

TERRAFORM_ARTIFACT = Path("/app/terraform")
VAR_EDGE_ARTIFACT = Path("/app/var/edge")
BASE_DATA = FIXTURES / "data"
VERIFIER_DATA = Path("/app/data")

REQUIRED_DISTRIBUTIONS = {"static-api", "failover", "signed-content"}

ENV = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
    "TF_IN_AUTOMATION": "1",
    "CHECKPOINT_DISABLE": "1",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
}


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), env=ENV, text=True, capture_output=True)


def _reset_verifier_data(overrides: dict[str, object] | None = None) -> None:
    if VERIFIER_DATA.exists():
        shutil.rmtree(VERIFIER_DATA)
    shutil.copytree(BASE_DATA, VERIFIER_DATA)
    if overrides:
        for filename, content in overrides.items():
            (VERIFIER_DATA / filename).write_text(
                json.dumps(content, indent=2), encoding="utf-8"
            )


def _load_base(filename: str) -> object:
    return json.loads((BASE_DATA / filename).read_text(encoding="utf-8"))


def _fresh_submission_copy(dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        TERRAFORM_ARTIFACT,
        dest,
        ignore=shutil.ignore_patterns(
            ".terraform", ".terraform.lock.hcl", "*.tfstate*", "tfplan"
        ),
    )
    return dest


def _plan(workspace: Path) -> subprocess.CompletedProcess:
    init = _run(["terraform", "init", "-backend=false", "-input=false"], workspace)
    if init.returncode != 0:
        return init
    return _run(
        ["terraform", "plan", "-refresh=false", "-input=false", "-out=tfplan", "-no-color"],
        workspace,
    )


def _show(workspace: Path) -> dict:
    proc = _run(["terraform", "show", "-json", "tfplan"], workspace)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def _replan(workspace: Path) -> tuple[dict | None, subprocess.CompletedProcess]:
    proc = _plan(workspace)
    if proc.returncode != 0:
        return None, proc
    return _show(workspace), proc


def _compute_evidence(plan: dict, graph: dict, probes: list[dict]) -> dict:
    """Reproduce edge_lab.write_evidence's fields without touching disk."""
    status = "READY" if all(p.get("ok") for p in probes) else "FAILED"
    stable = {
        "status": status,
        "plan_digest": edge_lab.plan_digest(plan),
        "probe_results": probes,
        "oac_present": graph.get("oac_present"),
    }
    digest = hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**stable, "evidence_digest": digest}


def _regenerate(workspace: Path) -> tuple[dict, dict, list[dict], dict]:
    """Plan, run the probe battery, and return (plan, graph, probes, evidence)."""
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    graph = edge_lab.normalize_plan(plan)
    state, servers, edge_urls = edge_lab.start_lab(graph)
    try:
        probes = edge_lab.run_probes(edge_urls, state)
    finally:
        edge_lab.stop_lab(servers)
    evidence = _compute_evidence(plan, graph, probes)
    return plan, graph, probes, evidence


@pytest.fixture(autouse=True)
def _clean_data():
    _reset_verifier_data()
    yield
    _reset_verifier_data()


@pytest.fixture(scope="session")
def submission_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dest = tmp_path_factory.mktemp("submission") / "terraform"
    return _fresh_submission_copy(dest)


@pytest.fixture(scope="session")
def agent_evidence() -> dict:
    path = VAR_EDGE_ARTIFACT / "cutover-evidence.json"
    assert path.is_file(), "missing /app/var/edge/cutover-evidence.json artifact"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def baseline_regeneration(submission_dir: Path) -> tuple[dict, dict, list[dict], dict]:
    """One independent replan + probe run against baseline policy inputs."""
    _reset_verifier_data()
    workspace = submission_dir / "workspaces" / "edge"
    return _regenerate(workspace)


def test_submitted_module_and_workspace_layout_present(submission_dir: Path):
    """The submitted module and workspace must exist with the required files."""
    module = submission_dir / "modules" / "edge"
    workspace = submission_dir / "workspaces" / "edge"
    for f in ("main.tf", "variables.tf", "outputs.tf", "versions.tf"):
        assert (module / f).is_file(), f"missing module file {f}"
    assert (workspace / "main.tf").is_file(), "missing workspace main.tf"


def test_agent_artifacts_exist_and_parse():
    """The agent must leave a regenerated plan and cutover evidence behind."""
    plan_path = VAR_EDGE_ARTIFACT / "plan.json"
    evidence_path = VAR_EDGE_ARTIFACT / "cutover-evidence.json"
    assert plan_path.is_file(), "missing /app/var/edge/plan.json"
    assert evidence_path.is_file(), "missing /app/var/edge/cutover-evidence.json"
    json.loads(plan_path.read_text(encoding="utf-8"))
    json.loads(evidence_path.read_text(encoding="utf-8"))


def test_agent_evidence_ready_with_passing_probes(agent_evidence: dict):
    """The agent's own cutover run must report READY with every probe passing."""
    assert agent_evidence.get("status") == "READY", agent_evidence.get("probe_results")
    probes = agent_evidence.get("probe_results") or []
    assert probes, "evidence has no probe_results"
    failing = [p["name"] for p in probes if not p.get("ok")]
    assert not failing, f"probes failed: {failing}"
    assert agent_evidence.get("evidence_digest")


def test_replan_from_submitted_module_matches_recorded_digest(
    baseline_regeneration: tuple[dict, dict, list[dict], dict],
    agent_evidence: dict,
):
    """An independent verifier replan of the submitted module must reproduce the
    plan digest the agent recorded, proving the evidence was not hand-written."""
    plan, _graph, probes, evidence = baseline_regeneration
    assert all(p.get("ok") for p in probes), probes
    assert evidence["plan_digest"] == agent_evidence["plan_digest"]


def test_plan_graph_matches_edge_contract(
    baseline_regeneration: tuple[dict, dict, list[dict], dict],
):
    """The resolved plan must show OAC-backed origins, no legacy s3_origin_config,
    an attached security headers policy, correct TLS floor, and S3-form logging."""
    _plan, graph, _probes, _evidence = baseline_regeneration
    assert graph["oac_present"] is True
    assert graph["has_s3_origin_config"] is False
    assert graph["headers_ok"] is True
    assert graph["signed_trusted_on_default"] is False
    assert graph["waf_name"]
    tls = graph.get("tls") or {}
    assert set(tls) == REQUIRED_DISTRIBUTIONS
    assert all(v == "TLSv1.2_2021" for v in tls.values())
    hosts = graph.get("logging_hosts") or {}
    assert set(hosts) == REQUIRED_DISTRIBUTIONS
    assert all((h or "").endswith(".s3.amazonaws.com") for h in hosts.values())


def test_second_independent_replan_evidence_digest_is_stable(submission_dir: Path):
    """Two independent verifier replans of the same submitted module against the
    same policy inputs must produce an identical evidence digest (no-op rerun)."""
    workspace = submission_dir / "workspaces" / "edge"
    _reset_verifier_data()
    _plan1, _g1, _p1, ev1 = _regenerate(workspace)
    _reset_verifier_data()
    _plan2, _g2, _p2, ev2 = _regenerate(workspace)
    assert ev1["evidence_digest"] == ev2["evidence_digest"]
    assert ev1["status"] == "READY"
    assert ev2["status"] == "READY"


def test_hidden_variation_reordered_path_rules_still_ready(submission_dir: Path):
    """Reordering path_rules must not change routing precedence; the module is
    expected to resolve precedence from the rule's own priority field."""
    rules = copy.deepcopy(_load_base("path_rules.json"))
    reversed_rules = list(reversed(rules))
    assert reversed_rules != rules
    _reset_verifier_data(overrides={"path_rules.json": reversed_rules})
    workspace = submission_dir / "workspaces" / "edge"
    _plan, _graph, probes, evidence = _regenerate(workspace)
    failing = [p["name"] for p in probes if not p.get("ok")]
    assert not failing, f"probes failed after reordering path_rules: {failing}"
    assert evidence["status"] == "READY"


def test_invalid_public_access_allowed_fails_plan(submission_dir: Path):
    """An object origin flagged public_access_allowed must fail plan, not the lab."""
    origins = copy.deepcopy(_load_base("origins.json"))
    for o in origins:
        if o.get("type") == "s3":
            o["public_access_allowed"] = True
    _reset_verifier_data(overrides={"origins.json": origins})
    workspace = submission_dir / "workspaces" / "edge"
    proc = _plan(workspace)
    assert proc.returncode != 0, "plan should fail for public_access_allowed=true"


def test_invalid_expired_signed_exception_fails_closed(submission_dir: Path):
    """An exception that has expired relative to the lab clock must not grant
    signed access; the cutover must not report READY."""
    exceptions = copy.deepcopy(_load_base("exception_requests.json"))
    for e in exceptions:
        e["expires_on"] = "2020-01-01"
    _reset_verifier_data(overrides={"exception_requests.json": exceptions})
    workspace = submission_dir / "workspaces" / "edge"
    proc = _plan(workspace)
    if proc.returncode != 0:
        return
    plan = _show(workspace)
    graph = edge_lab.normalize_plan(plan)
    state, servers, edge_urls = edge_lab.start_lab(graph)
    try:
        probes = edge_lab.run_probes(edge_urls, state)
    finally:
        edge_lab.stop_lab(servers)
    status = "READY" if all(p.get("ok") for p in probes) else "FAILED"
    assert status == "FAILED", "expired exception must not still grant signed access"


def test_counterexample_ready_status_requires_real_oac(
    baseline_regeneration: tuple[dict, dict, list[dict], dict],
):
    """A plan tampered to drop its OAC resources must fail the probe battery even
    though every other planned value is untouched (anti-cheat sanity check)."""
    plan, _graph, _probes, _evidence = baseline_regeneration
    tampered = copy.deepcopy(plan)

    def _strip_oac(module: dict) -> None:
        resources = module.get("resources") or []
        module["resources"] = [
            r for r in resources if r.get("type") != "aws_cloudfront_origin_access_control"
        ]
        for child in module.get("child_modules") or []:
            _strip_oac(child)

    _strip_oac(tampered["planned_values"]["root_module"])
    graph = edge_lab.normalize_plan(tampered)
    assert graph["oac_present"] is False
    state, servers, edge_urls = edge_lab.start_lab(graph)
    try:
        probes = edge_lab.run_probes(edge_urls, state)
    finally:
        edge_lab.stop_lab(servers)
    status = "READY" if all(p.get("ok") for p in probes) else "FAILED"
    assert status == "FAILED", "dropping OAC resources must not still read READY"
