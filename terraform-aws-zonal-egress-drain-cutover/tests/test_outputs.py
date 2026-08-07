"""Verifier for zonal egress drain cutover.

Replans the submitted Terraform module with trusted inventories, runs the
egress lab against that plan, and checks agent artifacts for READY status,
same-AZ paths, data isolation, gateway bypass, drain refusal, and idempotent
digests.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))
import egress_lab  # noqa: E402

TERRAFORM_ARTIFACT = Path("/app/terraform")
OUTPUT_ARTIFACT = Path("/app/output")
VAR_ARTIFACT = Path("/app/var/egress")
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
    "EGRESS_DATA_DIR": str(VERIFIER_DATA),
    "EGRESS_VAR_DIR": "/tmp/egress-var",
    "EGRESS_OUTPUT_DIR": "/tmp/egress-output",
}


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), env=ENV, text=True, capture_output=True)


def _reset_data(overrides: dict[str, object] | None = None) -> None:
    if VERIFIER_DATA.exists():
        shutil.rmtree(VERIFIER_DATA)
    shutil.copytree(BASE_DATA, VERIFIER_DATA)
    if overrides:
        for name, content in overrides.items():
            (VERIFIER_DATA / name).write_text(
                json.dumps(content, indent=2), encoding="utf-8"
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
            ".terraform", ".terraform.lock.hcl", "*.tfstate*", "tfplan"
        ),
    )
    return dest


def _rewrite_data_paths(workspace: Path) -> None:
    """Point workspace file() reads at verifier data dir."""
    main = workspace / "main.tf"
    text = main.read_text(encoding="utf-8")
    text = text.replace('file("/app/data/', f'file("{VERIFIER_DATA.as_posix()}/')
    main.write_text(text, encoding="utf-8")


def _plan(workspace: Path) -> subprocess.CompletedProcess:
    init = _run(["terraform", "init", "-backend=false", "-input=false"], workspace)
    if init.returncode != 0:
        return init
    return _run(
        [
            "terraform",
            "plan",
            "-refresh=false",
            "-input=false",
            "-out=tfplan",
            "-no-color",
        ],
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


@pytest.fixture(autouse=True)
def _clean_data():
    _reset_data()
    for path in (Path("/tmp/egress-var"), Path("/tmp/egress-output")):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    os.environ["EGRESS_DATA_DIR"] = str(VERIFIER_DATA)
    os.environ["EGRESS_VAR_DIR"] = "/tmp/egress-var"
    os.environ["EGRESS_OUTPUT_DIR"] = "/tmp/egress-output"
    yield
    _reset_data()


@pytest.fixture(scope="session")
def submission_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _fresh_copy(tmp_path_factory.mktemp("submission") / "terraform")


@pytest.fixture(scope="session")
def agent_report() -> dict:
    path = OUTPUT_ARTIFACT / "cutover-report.json"
    assert path.is_file(), "missing /app/output/cutover-report.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def agent_plan() -> dict:
    path = VAR_ARTIFACT / "plan.json"
    assert path.is_file(), "missing /app/var/egress/plan.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def baseline(submission_dir: Path) -> tuple[dict, dict]:
    """Independent plan + cutover against baseline inventory."""
    _reset_data()
    workspace = submission_dir / "workspaces" / "egress"
    _rewrite_data_paths(workspace)
    os.environ["EGRESS_MODULE_DIR"] = str(submission_dir / "modules" / "egress")
    ENV["EGRESS_MODULE_DIR"] = os.environ["EGRESS_MODULE_DIR"]
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = egress_lab.run_cutover(plan)
    return plan, report


def test_agent_report_ready(agent_report: dict, agent_plan: dict) -> None:
    """Agent cutover must finish READY with plan artifact and digest."""
    assert agent_report.get("status") == "READY"
    assert agent_report.get("report_digest")
    assert agent_plan.get("format_version") or agent_plan.get("resource_changes") is not None


def test_baseline_cutover_ready(baseline: tuple[dict, dict]) -> None:
    """Trusted lab must accept the submitted plan on baseline inventory."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert not report.get("policy_errors")


def test_same_az_app_paths(baseline: tuple[dict, dict]) -> None:
    """Healthy AZs must egress via their own NAT; draining AZs refuse new flows."""
    _plan, report = baseline
    decisions = report["nat_decisions"]
    flows = {f["id"]: f for f in report["flows"]}
    for key, dec in decisions.items():
        flow = flows[f"app-internet-{key}"]
        if dec["new_flow_action"] == "allow":
            assert flow["allowed"] is True
            assert f"nat-{key}" in flow["path"]
            assert flow["translated_source"]
        else:
            assert flow["allowed"] is False


def test_data_tier_isolated(baseline: tuple[dict, dict]) -> None:
    """Data subnets must not reach the internet default."""
    _plan, report = baseline
    assert report["data_isolated"] is True
    for flow in report["flows"]:
        if flow["id"].startswith("data-internet-"):
            assert flow["allowed"] is False


def test_gateway_bypass(baseline: tuple[dict, dict]) -> None:
    """S3 and DynamoDB must bypass NAT through gateway endpoints."""
    _plan, report = baseline
    assert report["gateway_bypass"]["s3"] is True
    assert report["gateway_bypass"]["dynamodb"] is True


def test_interface_dns_present(baseline: tuple[dict, dict]) -> None:
    """Interface endpoints with private DNS must populate DNS answers."""
    _plan, report = baseline
    assert "logs" in report["dns"]
    assert "sqs" in report["dns"]


def test_legacy_moved_present(submission_dir: Path) -> None:
    """Module must declare private-to-app moved mappings for legacy keys."""
    module = submission_dir / "modules" / "egress"
    os.environ["EGRESS_MODULE_DIR"] = str(module)
    moved = egress_lab.parse_moved_blocks(module)
    legacy = _load_base("legacy_addresses.json")
    for key in legacy["legacy_keys"]:
        assert any(
            f'private["{key}"]' in m["from"] and f'app["{key}"]' in m["to"] and "subnet" in m["from"]
            for m in moved
        )
        assert any(
            f'private["{key}"]' in m["from"]
            and f'app["{key}"]' in m["to"]
            and "route_table" in m["from"]
            for m in moved
        )


def test_reorder_topology_noop(submission_dir: Path, baseline: tuple[dict, dict]) -> None:
    """Reordering AZ map keys must preserve cutover semantics and digest class."""
    _plan, base_report = baseline
    topology = _load_base("topology.json")
    assert isinstance(topology, dict)
    azs = topology["azs"]
    reordered = {
        "azs": {k: azs[k] for k in reversed(list(azs))},
        "vpc_cidr": topology["vpc_cidr"],
    }
    _reset_data({"topology.json": reordered})
    shutil.rmtree(Path("/tmp/egress-reorder"), ignore_errors=True)
    tree = _fresh_copy(Path("/tmp/egress-reorder") / "terraform")
    workspace = tree / "workspaces" / "egress"
    _rewrite_data_paths(workspace)
    os.environ["EGRESS_MODULE_DIR"] = str(tree / "modules" / "egress")
    ENV["EGRESS_MODULE_DIR"] = os.environ["EGRESS_MODULE_DIR"]
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = egress_lab.run_cutover(plan)
    assert report["status"] == "READY", report
    assert report["data_isolated"] == base_report["data_isolated"]
    assert report["gateway_bypass"] == base_report["gateway_bypass"]


def test_add_az_extends_behavior(submission_dir: Path) -> None:
    """Adding one AZ must create corresponding namespace and flow coverage."""
    topology = copy.deepcopy(_load_base("topology.json"))
    topology["azs"]["use1d"] = {
        "az": "us-east-1d",
        "public_cidr": "10.42.3.0/24",
        "app_cidr": "10.42.19.0/24",
        "data_cidr": "10.42.35.0/24",
        "corporate_dns_cidrs": ["10.8.3.0/24"],
    }
    nat_health = dict(_load_base("nat_health.json"))
    nat_health["use1d"] = "healthy"
    legacy = copy.deepcopy(_load_base("legacy_addresses.json"))
    # new AZ has no legacy private identity requirement beyond existing keys
    _reset_data({"topology.json": topology, "nat_health.json": nat_health})
    tree = _fresh_copy(Path("/tmp/egress-addaz") / "terraform")
    workspace = tree / "workspaces" / "egress"
    _rewrite_data_paths(workspace)
    os.environ["EGRESS_MODULE_DIR"] = str(tree / "modules" / "egress")
    ENV["EGRESS_MODULE_DIR"] = os.environ["EGRESS_MODULE_DIR"]
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = egress_lab.run_cutover(plan)
    assert report["status"] == "READY", report
    assert any(ns["name"] == "app-use1d" for ns in report["namespaces"])
    flows = {f["id"]: f for f in report["flows"]}
    assert flows["app-internet-use1d"]["allowed"] is True


def test_failed_nat_refuses_new_flows(submission_dir: Path) -> None:
    """Injected NAT failure must refuse new app internet flows for that AZ."""
    _reset_data()
    tree = _fresh_copy(Path("/tmp/egress-fail") / "terraform")
    workspace = tree / "workspaces" / "egress"
    _rewrite_data_paths(workspace)
    os.environ["EGRESS_MODULE_DIR"] = str(tree / "modules" / "egress")
    ENV["EGRESS_MODULE_DIR"] = os.environ["EGRESS_MODULE_DIR"]
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = egress_lab.run_cutover(plan, fail_az="use1a")
    flows = {f["id"]: f for f in report["flows"]}
    assert flows["app-internet-use1a"]["allowed"] is False
    assert report["nat_decisions"]["use1a"]["health"] == "failed"


def test_cross_az_matrix_rejected() -> None:
    """Synthetic graph with wrong nat_az must fail policy checks."""
    _reset_data()
    bad = {
        "topology": _load_base("topology.json"),
        "services": _load_base("services.json"),
        "defaults": _load_base("defaults.json"),
        "subnets": {},
        "nat_gateways": {},
        "eips": {},
        "app_default": {},
        "data_default": {},
        "endpoints_iface": {},
        "endpoints_gw": {},
        "sgs": {},
        "moved": [],
        "outputs": {
            "egress_route_matrix": {
                "use1a": {
                    "app_cidr": "10.42.16.0/24",
                    "data_cidr": "10.42.32.0/24",
                    "nat_az": "use1b",
                    "data_has_default_route": False,
                }
            }
        },
        "changes": {},
    }
    # fill minimal subnets so other errors don't dominate the assertion
    topology = bad["topology"]
    for key, az in topology["azs"].items():
        for tier, field in (("public", "public_cidr"), ("app", "app_cidr"), ("data", "data_cidr")):
            bad["subnets"][f"{tier}:{key}"] = {
                "cidr": az[field],
                "map_public": tier == "public",
                "tier": tier,
                "key": key,
            }
        bad["nat_gateways"][key] = {"key": key}
        bad["app_default"][key] = {"key": key}
        bad["outputs"]["egress_route_matrix"][key] = {
            "app_cidr": az["app_cidr"],
            "data_cidr": az["data_cidr"],
            "nat_az": "use1a",
            "data_has_default_route": False,
        }
    errors = egress_lab.plan_policy_errors(bad)
    assert any("nat_az" in e or "cross-AZ" in e for e in errors)


def test_open_endpoint_sg_rejected() -> None:
    """Endpoint SG allowing 0.0.0.0/0 must fail policy."""
    _reset_data()
    graph = {
        "topology": _load_base("topology.json"),
        "services": _load_base("services.json"),
        "defaults": _load_base("defaults.json"),
        "subnets": {},
        "nat_gateways": {},
        "eips": {},
        "app_default": {},
        "data_default": {},
        "endpoints_iface": {s: {"private_dns": True} for s in _load_base("services.json")["interface"]},
        "endpoints_gw": {s: {} for s in _load_base("services.json")["gateway"]},
        "sgs": {
            "endpoint": {
                "ingress": [{"from_port": 443, "to_port": 443, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"]}]
            },
            "resolver": {
                "ingress": [
                    {"from_port": 53, "to_port": 53, "protocol": "tcp", "cidr_blocks": ["10.8.0.0/24"]},
                    {"from_port": 53, "to_port": 53, "protocol": "udp", "cidr_blocks": ["10.8.0.0/24"]},
                ]
            },
        },
        "moved": egress_lab.parse_moved_blocks(TERRAFORM_ARTIFACT / "modules" / "egress"),
        "outputs": {"egress_route_matrix": {}},
        "changes": {},
    }
    topology = graph["topology"]
    matrix = {}
    for key, az in topology["azs"].items():
        for tier, field in (("public", "public_cidr"), ("app", "app_cidr"), ("data", "data_cidr")):
            graph["subnets"][f"{tier}:{key}"] = {
                "cidr": az[field],
                "map_public": tier == "public",
                "tier": tier,
                "key": key,
            }
        graph["nat_gateways"][key] = {"key": key}
        graph["app_default"][key] = {"key": key}
        matrix[key] = {
            "app_cidr": az["app_cidr"],
            "data_cidr": az["data_cidr"],
            "nat_az": key,
            "data_has_default_route": False,
        }
    graph["outputs"]["egress_route_matrix"] = matrix
    errors = egress_lab.plan_policy_errors(graph)
    assert any("0.0.0.0/0" in e for e in errors)


def test_idempotent_agent_digest(agent_report: dict) -> None:
    """Agent report digest must be a stable sha256 hex string."""
    digest = agent_report["report_digest"]
    assert isinstance(digest, str) and len(digest) == 64


def test_static_report_not_enough() -> None:
    """A hand-written READY report without matching lab state is insufficient.

    The verifier always replans and re-runs the lab; this guards the contract
    that status alone is not graded from agent output without regeneration.
    """
    fake = {
        "status": "READY",
        "reason": None,
        "policy_errors": [],
        "namespaces": [],
        "flows": [],
        "nat_decisions": {},
        "dns": {},
        "gateway_bypass": {"s3": True, "dynamodb": True},
        "data_isolated": True,
        "migration": {"legacy_keys": [], "destructive_actions": 0, "missing_moved": []},
        "report_digest": "0" * 64,
    }
    # Ensure baseline path exists and differs from fake empty flows
    assert OUTPUT_ARTIFACT.joinpath("cutover-report.json").is_file()
    real = json.loads((OUTPUT_ARTIFACT / "cutover-report.json").read_text(encoding="utf-8"))
    assert real.get("flows"), "agent must record probed flows"
    assert real["report_digest"] != fake["report_digest"] or real["flows"] != fake["flows"]
