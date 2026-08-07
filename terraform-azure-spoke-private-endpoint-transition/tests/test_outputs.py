"""Verifier for Azure spoke private-endpoint transition.

Replans submitted Terraform with trusted topologies, runs the network/DNS lab,
and checks egress, NSG, private DNS, diagnostics, DDoS, locks, governance tags,
hidden variants, invalid inputs, legacy-state moves, and anti-cheat cases.
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
import sys

sys.path.insert(0, str(FIXTURES))
import spoke_lab  # noqa: E402

TERRAFORM_ARTIFACT = Path("/app/terraform")
OUTPUT_ARTIFACT = Path("/app/output")
VAR_ARTIFACT = Path("/app/var/spoke")
BASE_DATA = FIXTURES / "data"
VERIFIER_DATA = Path("/app/data")

ENV = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
    "TF_IN_AUTOMATION": "1",
    "CHECKPOINT_DISABLE": "1",
    "ARM_SUBSCRIPTION_ID": "00000000-0000-0000-0000-000000000000",
    "ARM_TENANT_ID": "00000000-0000-0000-0000-000000000000",
    "ARM_CLIENT_ID": "00000000-0000-0000-0000-000000000001",
    "ARM_CLIENT_SECRET": "not-used-by-mock",
    "SPOKE_DATA_DIR": str(VERIFIER_DATA),
    "SPOKE_VAR_DIR": "/tmp/spoke-var",
    "SPOKE_OUTPUT_DIR": "/tmp/spoke-output",
}

os.environ.update(
    {
        "SPOKE_DATA_DIR": str(VERIFIER_DATA),
        "SPOKE_VAR_DIR": "/tmp/spoke-var",
        "SPOKE_OUTPUT_DIR": "/tmp/spoke-output",
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


def _module_sources(root: Path) -> str:
    texts = []
    for path in (root / "modules" / "spoke").rglob("*.tf"):
        texts.append(path.read_text(encoding="utf-8"))
    return "\n".join(texts)


@pytest.fixture(autouse=True)
def _clean_data():
    _reset_data()
    for path in (Path("/tmp/spoke-var"), Path("/tmp/spoke-output")):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    yield
    _reset_data()


@pytest.fixture(scope="session")
def submission_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _fresh_copy(tmp_path_factory.mktemp("submission") / "terraform")


@pytest.fixture(scope="session")
def agent_report() -> dict:
    path = OUTPUT_ARTIFACT / "transition-report.json"
    assert path.is_file(), "missing /app/output/transition-report.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def agent_probes() -> dict:
    path = OUTPUT_ARTIFACT / "network-probes.json"
    assert path.is_file(), "missing /app/output/network-probes.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def agent_plan() -> dict:
    path = VAR_ARTIFACT / "plan.json"
    assert path.is_file(), "missing /app/var/spoke/plan.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def baseline(submission_dir: Path) -> tuple[dict, dict]:
    """Independent plan + lab against baseline topology."""
    _reset_data()
    workspace = submission_dir / "workspaces" / "spoke"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = spoke_lab.run_transition(plan)
    return plan, report


def test_agent_artifacts_ready(
    agent_report: dict, agent_probes: dict, agent_plan: dict
) -> None:
    """Agent transition must finish READY with plan, probes, and digest."""
    assert agent_report.get("status") == "READY"
    assert agent_report.get("report_digest")
    assert agent_probes.get("dns")
    assert agent_plan.get("resource_changes")


def test_baseline_lab_ready(baseline: tuple[dict, dict]) -> None:
    """Trusted lab must accept the submitted plan on baseline topology."""
    _plan, report = baseline
    assert report["status"] == "READY", report.get("policy_errors")
    assert not report.get("policy_errors")


def test_egress_through_firewall(baseline: tuple[dict, dict]) -> None:
    """App and data UDRs must use VirtualAppliance firewall next hop."""
    _plan, report = baseline
    for key in ("app", "data"):
        eg = report["egress"][key]
        assert eg["routed"] is True
        assert eg["next_hop_type"] == "VirtualAppliance"
        assert eg["next_hop_ip"] == "10.42.255.4"
    assert report["egress"]["private-endpoints"]["routed"] is False
    assert report["egress"]["AzureBastionSubnet"]["routed"] is False


def test_nsg_and_dns_probes(baseline: tuple[dict, dict]) -> None:
    """NSG allow/deny probes and private DNS usability must agree."""
    _plan, report = baseline
    flows = {d["flow"]: d["result"] for d in report["nsg_decisions"]}
    assert flows["agw_to_app_443"] == "Allow"
    assert flows["app_to_data_5432"] == "Allow"
    assert flows["internet_to_app"] == "Deny"
    assert all(d["usable"] for d in report["dns"])
    assert report["dns_zone_count"] == 4
    assert report["lock_present"] is True
    assert report["ddos_attached"] is False


def test_governance_tags_win(baseline: tuple[dict, dict]) -> None:
    """Required governance tags override conflicting caller tags."""
    _plan, report = baseline
    tags = report["governance_tags"]
    assert tags.get("managed_by") == "terraform"
    assert tags.get("data_classification") == "regulated"
    assert tags.get("business_unit") == "payments"
    assert tags.get("environment") == "prod"


def test_diagnostics_cover_vnet_and_nsgs(baseline: tuple[dict, dict]) -> None:
    """Diagnostics must cover the VNet and every managed NSG."""
    _plan, report = baseline
    assert report["diagnostic_count"] >= 1 + len(report["nsg_keys"])
    assert set(report["nsg_keys"]) >= {"app", "data"}


def test_reorder_topology_noop(submission_dir: Path, baseline: tuple[dict, dict]) -> None:
    """Reordering subnet and endpoint maps must preserve report semantics."""
    _plan0, report0 = baseline
    topo = copy.deepcopy(_load_base("topology.json"))
    assert isinstance(topo, dict)
    subnets = topo["subnets"]
    assert isinstance(subnets, dict)
    topo["subnets"] = {k: subnets[k] for k in reversed(list(subnets.keys()))}
    endpoints = topo["private_endpoints"]
    assert isinstance(endpoints, dict)
    topo["private_endpoints"] = {
        k: endpoints[k] for k in reversed(list(endpoints.keys()))
    }
    _reset_data({"topology.json": topo})
    workspace = _fresh_copy(Path("/tmp/spoke-reorder") / "terraform") / "workspaces" / "spoke"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = spoke_lab.run_transition(plan)
    assert report["status"] == "READY", report.get("policy_errors")
    assert report["subnet_keys"] == report0["subnet_keys"]
    assert report["endpoint_keys"] == report0["endpoint_keys"]
    assert report["report_digest"] == report0["report_digest"]


def test_expand_endpoint_and_nsg(submission_dir: Path) -> None:
    """Adding one endpoint and one nsg-enabled subnet changes only those keys."""
    topo = copy.deepcopy(_load_base("topology.json"))
    assert isinstance(topo, dict)
    topo["subnets"]["ops"] = {
        "address_prefixes": ["10.42.50.0/24"],
        "tier": "app",
        "route_table_enabled": True,
        "nsg_enabled": True,
    }
    topo["private_endpoints"]["pg"] = {
        "target_resource_id": (
            "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/"
            "rg-data/providers/Microsoft.DBforPostgreSQL/flexibleServers/pay-pg"
        ),
        "subresource_names": ["postgresqlServer"],
        "dns_zone_key": "postgresql",
    }
    _reset_data({"topology.json": topo})
    workspace = _fresh_copy(Path("/tmp/spoke-expand") / "terraform") / "workspaces" / "spoke"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = spoke_lab.run_transition(plan)
    assert report["status"] == "READY", report.get("policy_errors")
    assert "ops" in report["subnet_keys"]
    assert "ops" in report["nsg_keys"]
    assert "pg" in report["endpoint_keys"]


def test_ddos_toggle(submission_dir: Path) -> None:
    """Enabling DDoS must attach the supplied plan id."""
    topo = copy.deepcopy(_load_base("topology.json"))
    assert isinstance(topo, dict)
    topo["enable_ddos_protection"] = True
    _reset_data({"topology.json": topo})
    workspace = _fresh_copy(Path("/tmp/spoke-ddos") / "terraform") / "workspaces" / "spoke"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = spoke_lab.run_transition(plan)
    assert report["status"] == "READY", report.get("policy_errors")
    assert report["ddos_attached"] is True


def test_invalid_endpoint_subnet_key_fails(submission_dir: Path) -> None:
    """Invalid private_endpoint_subnet_key must fail before a READY report."""
    topo = copy.deepcopy(_load_base("topology.json"))
    assert isinstance(topo, dict)
    topo["private_endpoint_subnet_key"] = "does-not-exist"
    _reset_data({"topology.json": topo})
    workspace = _fresh_copy(Path("/tmp/spoke-badpe") / "terraform") / "workspaces" / "spoke"
    plan, proc = _replan(workspace)
    if plan is None:
        assert proc.returncode != 0
        return
    report = spoke_lab.run_transition(plan)
    assert report["status"] == "FAILED"


def test_open_admin_cidr_rejected(submission_dir: Path) -> None:
    """Open administrator CIDRs must fail plan or lab validation."""
    topo = copy.deepcopy(_load_base("topology.json"))
    assert isinstance(topo, dict)
    topo["allowed_admin_cidrs"] = ["0.0.0.0/0"]
    _reset_data({"topology.json": topo})
    workspace = _fresh_copy(Path("/tmp/spoke-admin") / "terraform") / "workspaces" / "spoke"
    plan, proc = _replan(workspace)
    if plan is None:
        assert proc.returncode != 0
        return
    report = spoke_lab.run_transition(plan)
    assert report["status"] == "FAILED"
    assert any("allowed_admin_cidrs" in e for e in report["policy_errors"])


def test_legacy_state_moves(submission_dir: Path) -> None:
    """Plan against legacy singleton state must not destroy moved identities."""
    src = _module_sources(submission_dir)
    for legacy in (
        "azurerm_subnet.app",
        "azurerm_subnet.data",
        "azurerm_route_table.default",
        "azurerm_subnet_route_table_association.app",
    ):
        assert f"from = {legacy}" in src or f"from={legacy}" in src.replace(" ", "")

    workspace = _fresh_copy(Path("/tmp/spoke-legacy") / "terraform") / "workspaces" / "spoke"
    # Seed a minimal prior state with legacy addresses inside the module.
    init = _run(["terraform", "init", "-backend=false", "-input=false"], workspace)
    assert init.returncode == 0, init.stdout + init.stderr

    state = {
        "version": 4,
        "terraform_version": "1.9.8",
        "serial": 1,
        "lineage": "11111111-1111-1111-1111-111111111111",
        "outputs": {},
        "resources": [
            {
                "module": "module.spoke",
                "mode": "managed",
                "type": "azurerm_subnet",
                "name": "app",
                "provider": "provider[\"registry.terraform.io/hashicorp/azurerm\"]",
                "instances": [
                    {
                        "schema_version": 0,
                        "attributes": {
                            "id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-pay-prod-network/providers/Microsoft.Network/virtualNetworks/pay-prod-spoke/subnets/app",
                            "name": "app",
                            "resource_group_name": "rg-pay-prod-network",
                            "virtual_network_name": "pay-prod-spoke",
                            "address_prefixes": ["10.42.10.0/24"],
                            "private_endpoint_network_policies": "Enabled",
                        },
                    }
                ],
            },
            {
                "module": "module.spoke",
                "mode": "managed",
                "type": "azurerm_subnet",
                "name": "data",
                "provider": "provider[\"registry.terraform.io/hashicorp/azurerm\"]",
                "instances": [
                    {
                        "schema_version": 0,
                        "attributes": {
                            "id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-pay-prod-network/providers/Microsoft.Network/virtualNetworks/pay-prod-spoke/subnets/data",
                            "name": "data",
                            "resource_group_name": "rg-pay-prod-network",
                            "virtual_network_name": "pay-prod-spoke",
                            "address_prefixes": ["10.42.20.0/24"],
                            "private_endpoint_network_policies": "Enabled",
                        },
                    }
                ],
            },
        ],
    }
    (workspace / "terraform.tfstate").write_text(json.dumps(state), encoding="utf-8")
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    for rc in plan.get("resource_changes") or []:
        addr = rc.get("address") or ""
        actions = (rc.get("change") or {}).get("actions") or []
        if "module.spoke.azurerm_subnet.spoke[\"app\"]" in addr or addr.endswith(
            'azurerm_subnet.spoke["app"]'
        ):
            assert "delete" not in actions or "create" not in actions
            assert actions != ["delete", "create"]
        if "module.spoke.azurerm_subnet.spoke[\"data\"]" in addr or addr.endswith(
            'azurerm_subnet.spoke["data"]'
        ):
            assert actions != ["delete", "create"]


def test_idempotent_digest(baseline: tuple[dict, dict]) -> None:
    """Two lab runs on the same plan must share report_digest."""
    plan, report1 = baseline
    report2 = spoke_lab.run_transition(plan)
    assert report1["report_digest"] == report2["report_digest"]


def test_static_report_rejected(agent_report: dict) -> None:
    """A disconnected READY report without matching plan semantics fails lab."""
    _reset_data()
    fake_plan = {"resource_changes": []}
    report = spoke_lab.run_transition(fake_plan)
    assert report["status"] == "FAILED"
    assert agent_report["status"] == "READY"


def test_internet_route_graph_fails() -> None:
    """Synthetic graph with Internet next hop must fail policy checks."""
    topo = _load_base("topology.json")
    assert isinstance(topo, dict)
    graph = {
        "vnets": [{"name": "x", "address_space": ["10.42.0.0/16"], "tags": {}, "ddos": []}],
        "subnets": {
            "app": {
                "name": "app",
                "address_prefixes": ["10.42.10.0/24"],
                "private_endpoint_network_policies": "Enabled",
            }
        },
        "route_tables": {"app": {"name": "rt", "disable_bgp_route_propagation": True, "tags": {}}},
        "routes": [
            {
                "key": "app",
                "address_prefix": "0.0.0.0/0",
                "next_hop_type": "Internet",
                "next_hop_in_ip_address": None,
                "route_table_name": "rt",
                "address": 'azurerm_route.default_egress["app"]',
            }
        ],
        "rt_assocs": [],
        "nsgs": {},
        "nsg_rules": [],
        "nsg_assocs": [],
        "dns_zones": {},
        "dns_links": [],
        "endpoints": {},
        "diagnostics": [],
        "locks": [],
        "prior_resources": [],
        "resource_changes": [],
    }
    errors = spoke_lab.policy_errors(graph, topo, _load_base("governance.json"))
    assert any("Internet" in e for e in errors)


def test_harness_not_replaced(submission_dir: Path) -> None:
    """Submitted tree must still be real Terraform, not a report printer."""
    workspace = submission_dir / "workspaces" / "spoke"
    assert (workspace / "main.tf").is_file()
    assert (submission_dir / "modules" / "spoke").is_dir()
    tf_files = list((submission_dir / "modules" / "spoke").glob("*.tf"))
    assert tf_files
    blob = "\n".join(p.read_text(encoding="utf-8") for p in tf_files)
    assert "azurerm_virtual_network" in blob
    assert not re.search(r"print\s*\(\s*[\"']READY", blob)
