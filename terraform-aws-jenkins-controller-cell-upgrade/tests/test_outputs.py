"""Verifier for Jenkins controller cell isolation and upgrade.

Replans submitted Terraform with trusted inventories, loads submitted cell
deploy config, and runs the cell lab for READY status, exclusive homes,
cross-cell denial, restart preservation, failed-upgrade rollback, and
idempotent digests.
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
import yaml

FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))
import cell_lab  # noqa: E402

TERRAFORM_ARTIFACT = Path("/app/terraform")
CELLS_ARTIFACT = Path("/app/cells")
OUTPUT_ARTIFACT = Path("/app/output")
VAR_ARTIFACT = Path("/app/var/cells")
BASE_DATA = FIXTURES / "data"
VERIFIER_DATA = Path("/app/data")
VERIFIER_CELLS = Path("/tmp/cell-cells")

ENV = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
    "TF_IN_AUTOMATION": "1",
    "CHECKPOINT_DISABLE": "1",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
    "CELL_DATA_DIR": str(VERIFIER_DATA),
    "CELL_VAR_DIR": "/tmp/cell-var",
    "CELL_OUTPUT_DIR": "/tmp/cell-output",
    "CELL_CELLS_DIR": str(VERIFIER_CELLS),
}

os.environ.update(
    {
        "CELL_DATA_DIR": str(VERIFIER_DATA),
        "CELL_VAR_DIR": "/tmp/cell-var",
        "CELL_OUTPUT_DIR": "/tmp/cell-output",
        "CELL_CELLS_DIR": str(VERIFIER_CELLS),
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


def _reset_cells(source: Path | None = None) -> None:
    if VERIFIER_CELLS.exists():
        shutil.rmtree(VERIFIER_CELLS)
    src = source or CELLS_ARTIFACT
    shutil.copytree(src, VERIFIER_CELLS)


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


@pytest.fixture(autouse=True)
def _clean_data():
    _reset_data()
    _reset_cells()
    for path in (Path("/tmp/cell-var"), Path("/tmp/cell-output")):
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
    path = OUTPUT_ARTIFACT / "cell-upgrade-report.json"
    assert path.is_file(), "missing /app/output/cell-upgrade-report.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def baseline(submission_dir: Path) -> tuple[dict, dict]:
    """Independent plan + cell upgrade against baseline inventory."""
    _reset_data()
    _reset_cells()
    workspace = submission_dir / "workspaces" / "cells"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = cell_lab.run_upgrade(plan)
    return plan, report


def test_agent_report_ready(agent_report: dict) -> None:
    """Agent exercise must finish READY with a digest and three booted cells."""
    assert agent_report.get("status") == "READY"
    assert agent_report.get("report_digest")
    cells = agent_report.get("cells") or {}
    assert set(cells) >= {
        "payments-controller",
        "risk-controller",
        "platform-controller",
    }
    assert all(c.get("booted") and c.get("serving") for c in cells.values())


def test_agent_plan_artifact_present() -> None:
    """Public command must leave a regenerated terraform show JSON plan."""
    path = VAR_ARTIFACT / "plan.json"
    assert path.is_file(), "missing /app/var/cells/plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    assert plan.get("resource_changes")


def test_baseline_upgrade_ready(baseline: tuple[dict, dict]) -> None:
    """Trusted lab must accept the submitted plan and cell config."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert not report.get("policy_errors")


def test_cross_cell_jobs_denied(baseline: tuple[dict, dict]) -> None:
    """Jobs submitted to the wrong cell must be denied."""
    _plan, report = baseline
    assert report["isolation"]["cross_cell_denied"] is True
    denied = [r for r in report["job_runs"] if r["status"] == "CROSS_CELL_DENIED"]
    assert denied


def test_dual_writer_blocked(baseline: tuple[dict, dict]) -> None:
    """Each home claim must stay exclusively locked to one cell."""
    _plan, report = baseline
    assert report["isolation"]["dual_writer_blocked"] is True
    claims = [c["home_claim"] for c in report["cells"].values()]
    assert len(claims) == len(set(claims))


def test_restart_preserves_builds(baseline: tuple[dict, dict]) -> None:
    """Controller restart must keep completed build watermarks."""
    _plan, report = baseline
    assert report["restart"]["builds_preserved"] is True
    assert report["restart"]["cell"] == "payments-controller"


def test_failed_upgrade_rollback(baseline: tuple[dict, dict]) -> None:
    """Incompatible cell upgrade must fail, roll back, and keep siblings up."""
    _plan, report = baseline
    drill = report["upgrade_drill"]
    assert drill["target_cell"] == "risk-controller"
    assert drill["failed"] is True
    assert drill["rolled_back"] is True
    assert drill["builds_preserved"] is True
    assert drill["sibling_cells_serving"] is True
    assert report["disruption"]["pdb_respected"] is True
    assert report["disruption"]["other_cells_available"] is True


def test_shared_home_policy_rejected(baseline: tuple[dict, dict]) -> None:
    """A graph that remounts every cell on one claim must fail policy."""
    _plan, report = baseline
    graph = cell_lab.normalize_plan(_plan)
    for cell_id, meta in graph["cells"].items():
        meta["home_claim"] = "shared-jenkins-home"
        if "home" in meta:
            meta["home"]["home_claim"] = "shared-jenkins-home"
            meta["home"]["path"] = "/jenkins-home"
    inventory = _load_base("fleet_registry.json")
    topology = _load_base("node_topology.json")
    defaults = _load_base("defaults.json")
    catalog = _load_base("plugin_catalog.json")
    cells_cfg = {
        "registry": json.loads(
            (CELLS_ARTIFACT / "fleet-registry.json").read_text(encoding="utf-8")
        ),
        "restrictions": json.loads(
            (CELLS_ARTIFACT / "restrictions.json").read_text(encoding="utf-8")
        ),
        "catalog": yaml.safe_load(
            (CELLS_ARTIFACT / "plugin-catalog.yaml").read_text(encoding="utf-8")
        ),
        "jcasc": {
            p.stem: yaml.safe_load(p.read_text(encoding="utf-8"))
            for p in sorted((CELLS_ARTIFACT / "jcasc").glob("*.yaml"))
        },
    }
    errors = cell_lab.plan_policy_errors(
        graph, inventory, topology, defaults, catalog, cells_cfg
    )
    assert any("home" in e or "duplicate" in e for e in errors)


def test_public_plugin_source_rejected() -> None:
    """Public update-center provenance must fail before cells boot."""
    _reset_cells()
    restrictions = json.loads(
        (VERIFIER_CELLS / "restrictions.json").read_text(encoding="utf-8")
    )
    restrictions["plugin_source"] = "public-update-center"
    (VERIFIER_CELLS / "restrictions.json").write_text(
        json.dumps(restrictions, indent=2), encoding="utf-8"
    )
    catalog = yaml.safe_load(
        (VERIFIER_CELLS / "plugin-catalog.yaml").read_text(encoding="utf-8")
    )
    catalog["pluginSource"] = "public-update-center"
    (VERIFIER_CELLS / "plugin-catalog.yaml").write_text(
        yaml.safe_dump(catalog), encoding="utf-8"
    )
    inventory = _load_base("fleet_registry.json")
    topology = _load_base("node_topology.json")
    defaults = _load_base("defaults.json")
    plugin_catalog = _load_base("plugin_catalog.json")
    # Minimal graph with correct homes so provenance is the failing axis.
    graph = {
        "cells": {},
        "homes": {},
        "roles": {},
        "node_groups": {
            "jenkins_controllers": {
                "node_group_name": "jenkins_controllers",
                "labels": topology["labels"],
                "taints": topology["taints"],
                "min_size": 3,
                "desired_size": 3,
                "tags": {"MaxUnavailable": "0"},
            }
        },
        "ssm": {},
    }
    cells_cfg = cell_lab._load_cells_config()
    errors = cell_lab.plan_policy_errors(
        graph, inventory, topology, defaults, plugin_catalog, cells_cfg
    )
    assert any("plugin_source" in e or "catalog" in e for e in errors)


def test_reordered_registry_is_semantic_noop(submission_dir: Path) -> None:
    """Reordering fleet job maps must not change READY semantics."""
    inventory = _load_base("fleet_registry.json")
    jobs = inventory["jobs"]
    reordered = {k: jobs[k] for k in reversed(list(jobs.keys()))}
    inventory = {**inventory, "jobs": reordered}
    _reset_data({"fleet_registry.json": inventory})
    _reset_cells()
    # Keep cells registry job order different too.
    cells_reg = json.loads(
        (VERIFIER_CELLS / "fleet-registry.json").read_text(encoding="utf-8")
    )
    cells_reg["jobs"] = {
        k: cells_reg["jobs"][k] for k in reversed(list(cells_reg["jobs"].keys()))
    }
    (VERIFIER_CELLS / "fleet-registry.json").write_text(
        json.dumps(cells_reg, indent=2), encoding="utf-8"
    )
    workspace = submission_dir / "workspaces" / "cells"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = cell_lab.run_upgrade(plan)
    assert report["status"] == "READY", report


def test_hidden_extra_job_routes_to_owner(submission_dir: Path) -> None:
    """An added valid job must run only on its assigned cell."""
    _reset_data()
    _reset_cells()
    workspace = submission_dir / "workspaces" / "cells"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    extra = {
        "payments-hotfix": {
            "cell": "payments-controller",
            "folder": "payments",
            "required_plugins": ["git"],
        }
    }
    report = cell_lab.run_upgrade(plan, extra_jobs=extra)
    assert report["status"] == "READY", report
    hits = [r for r in report["job_runs"] if r["job"] == "payments-hotfix"]
    assert hits and hits[0]["cell"] == "payments-controller"
    assert hits[0]["status"] == "SUCCESS"


def test_incompatible_generation_fails_boot(submission_dir: Path) -> None:
    """Pinning a cell to gen-3-incompatible must fail closed."""
    _reset_data()
    _reset_cells()
    registry = json.loads(
        (VERIFIER_CELLS / "fleet-registry.json").read_text(encoding="utf-8")
    )
    registry["cells"]["risk-controller"]["plugin_generation"] = "gen-3-incompatible"
    (VERIFIER_CELLS / "fleet-registry.json").write_text(
        json.dumps(registry, indent=2), encoding="utf-8"
    )
    # Inventory must match for policy; force inventory generation too so boot path runs.
    inventory = _load_base("fleet_registry.json")
    inventory = copy.deepcopy(inventory)
    inventory["cells"]["risk-controller"]["plugin_generation"] = "gen-3-incompatible"
    _reset_data({"fleet_registry.json": inventory})
    # Fix cells registry again after reset_data doesn't touch cells — already set.
    workspace = submission_dir / "workspaces" / "cells"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    # Plan still has gen-2 from terraform reading original... wait, terraform reads
    # /app/data which we overwrote. So plan will have gen-3-incompatible.
    report = cell_lab.run_upgrade(plan)
    assert report["status"] == "FAILED"
    assert report["cells"]["risk-controller"]["booted"] is False


def test_idempotent_digest(submission_dir: Path) -> None:
    """Two clean lab runs with the same inputs must share a report digest."""
    _reset_data()
    _reset_cells()
    workspace = submission_dir / "workspaces" / "cells"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    first = cell_lab.run_upgrade(plan)
    second = cell_lab.run_upgrade(plan)
    assert first["status"] == "READY"
    assert first["report_digest"] == second["report_digest"]


def test_static_ready_report_is_insufficient() -> None:
    """Agent artifacts must include real plan/config and drill evidence."""
    assert (TERRAFORM_ARTIFACT / "workspaces" / "cells").is_dir()
    assert (CELLS_ARTIFACT / "fleet-registry.json").is_file()
    report_path = OUTPUT_ARTIFACT / "cell-upgrade-report.json"
    assert report_path.is_file(), "missing /app/output/cell-upgrade-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report.get("upgrade_drill", {}).get("rolled_back") is True
    assert report.get("isolation", {}).get("dual_writer_blocked") is True
