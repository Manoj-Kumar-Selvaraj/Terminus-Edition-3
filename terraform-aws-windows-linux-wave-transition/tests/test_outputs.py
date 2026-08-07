"""Verifier for the Windows→Linux wave transition rehearsal.

Replans the submitted Terraform tree with trusted inventories, runs the
wave lab against that plan, and checks agent artifacts for READY status,
dependency-ordered handoff, exclusive disk mounts, and idempotent digests.
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
import wave_lab  # noqa: E402

TERRAFORM_ARTIFACT = Path("/app/terraform")
OUTPUT_ARTIFACT = Path("/app/output")
VAR_ARTIFACT = Path("/app/var/wave")
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
    "WAVE_DATA_DIR": str(VERIFIER_DATA),
    "WAVE_VAR_DIR": "/tmp/wave-var",
    "WAVE_OUTPUT_DIR": "/tmp/wave-output",
}

# Ensure wave_lab path helpers see verifier isolation dirs.
os.environ.update(
    {
        "WAVE_DATA_DIR": str(VERIFIER_DATA),
        "WAVE_VAR_DIR": "/tmp/wave-var",
        "WAVE_OUTPUT_DIR": "/tmp/wave-output",
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


@pytest.fixture(autouse=True)
def _clean_data():
    _reset_data()
    for path in (Path("/tmp/wave-var"), Path("/tmp/wave-output")):
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
    path = OUTPUT_ARTIFACT / "rehearsal-report.json"
    assert path.is_file(), "missing /app/output/rehearsal-report.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def agent_journal() -> dict:
    path = OUTPUT_ARTIFACT / "cutover-journal.json"
    assert path.is_file(), "missing /app/output/cutover-journal.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def baseline(submission_dir: Path) -> tuple[dict, dict]:
    """Independent plan + rehearsal against baseline inventory."""
    _reset_data()
    workspace = submission_dir / "workspaces" / "wave"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = wave_lab.run_rehearsal(plan)
    return plan, report


def test_agent_report_ready(agent_report: dict, agent_journal: dict) -> None:
    """Agent rehearsal must finish READY with a journal and digest."""
    assert agent_report.get("status") == "READY"
    assert agent_report.get("report_digest")
    assert agent_journal.get("status") == "READY"
    assert agent_journal.get("wave_order")


def test_baseline_rehearsal_ready(baseline: tuple[dict, dict]) -> None:
    """Trusted lab must accept the submitted plan on baseline inventory."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert not report.get("policy_errors")


def test_handoff_respects_dependencies(baseline: tuple[dict, dict]) -> None:
    """claims-worker may hand off only after payments-api is Linux."""
    _plan, report = baseline
    handoffs = {h["workload"]: h for h in report["handoffs"]}
    assert handoffs["payments-api"]["writer"] == "linux"
    assert handoffs["claims-worker"]["writer"] == "linux"
    order = report["wave_order"]
    assert order.index("payments-api") < order.index("claims-worker")


def test_no_dual_mounts_on_success(baseline: tuple[dict, dict]) -> None:
    """Successful cutover must leave each snapshot under a single holder."""
    _plan, report = baseline
    mounts = report["mount_table"]
    holders = list(mounts.values())
    assert len(holders) == len(set(mounts.keys()))
    assert all(h.startswith("linux:") for h in holders)


def test_forbidden_groups_rejected() -> None:
    """Plan that retains RDP/WinRM groups must fail policy rehearsal."""
    _reset_data()
    # Use a deliberately broken copy: strip SSM filtering by rewriting nothing;
    # instead inject via defaults clearing forbidden list then check starter fails
    # when we force cmdb to keep forbidden groups AND defaults still forbid them.
    # Submission that is correct will still filter; so mutate defaults to empty
    # forbidden and then assert a synthetic bad graph fails.
    bad_graph = {
        "instances": {
            "payments-api": {
                "ami": "ami-linux-payments-20260601",
                "instance_type": "m7i.large",
                "subnet_id": "subnet-private-app-a",
                "private_ip": "10.42.16.21",
                "availability_zone": "us-east-1a",
                "vpc_security_group_ids": ["sg-payments-app", "sg-rdp-admin", "sg-ssm-egress"],
                "iam_instance_profile": "ssm-linux-core-prod",
                "associate_public_ip_address": False,
                "disable_api_termination": True,
                "monitoring": True,
                "ebs_optimized": True,
                "key_name": None,
                "metadata_http_tokens": "required",
                "metadata_hop_limit": 1,
                "root_encrypted": True,
                "root_kms_key_id": (
                    "arn:aws:kms:us-east-1:111122223333:key/"
                    "96b54ac0-1579-42db-8ed0-ec2linuxmigration"
                ),
                "root_volume_size": 80,
                "tags": {"Workload": "payments-api"},
            }
        },
        "volumes": {},
        "attachments": [],
    }
    cmdb = _load_base("cmdb.json")
    disks = _load_base("disks.json")
    defaults = _load_base("defaults.json")
    errors = wave_lab.plan_policy_errors(bad_graph, cmdb, disks, defaults)
    assert any("forbidden" in e for e in errors)


def test_mid_wave_failure_keeps_windows_writer(submission_dir: Path) -> None:
    """Injected health failure must leave Windows writer and avoid dual mounts."""
    _reset_data()
    workspace = submission_dir / "workspaces" / "wave"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = wave_lab.run_rehearsal(plan, fail_workload="claims-worker")
    assert report["status"] == "FAILED"
    handoffs = {h["workload"]: h for h in report["handoffs"]}
    assert handoffs["payments-api"]["writer"] == "linux"
    assert handoffs["claims-worker"]["writer"] == "windows"
    mounts = report["mount_table"]
    claims_snaps = [
        v["snapshot_id"] for v in json.loads((VERIFIER_DATA / "disks.json").read_text())["claims-worker"]
    ]
    for snap in claims_snaps:
        assert mounts.get(snap) == "windows:claims-worker"


def test_reordered_inventory_is_semantic_noop(submission_dir: Path) -> None:
    """Reordering CMDB/disk map keys must not change wave semantics."""
    cmdb = _load_base("cmdb.json")
    disks = _load_base("disks.json")
    reordered_cmdb = {k: cmdb[k] for k in reversed(list(cmdb.keys()))}
    reordered_disks = {k: disks[k] for k in reversed(list(disks.keys()))}
    _reset_data({"cmdb.json": reordered_cmdb, "disks.json": reordered_disks})
    workspace = submission_dir / "workspaces" / "wave"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = wave_lab.run_rehearsal(plan)
    assert report["status"] == "READY"
    assert "payments-api" in report["wave_order"]
    assert report["wave_order"].index("payments-api") < report["wave_order"].index(
        "claims-worker"
    )


def test_hidden_extra_workload(submission_dir: Path) -> None:
    """Adding a leaf workload expands handoff without breaking the base wave."""
    cmdb = copy.deepcopy(_load_base("cmdb.json"))
    disks = copy.deepcopy(_load_base("disks.json"))
    deps = copy.deepcopy(_load_base("dependencies.json"))
    windows = copy.deepcopy(_load_base("windows.json"))
    maint = copy.deepcopy(_load_base("maintenance.json"))
    checksums = copy.deepcopy(_load_base("checksums.json"))

    cmdb["batch-helper"] = {
        "workload": "batch-helper",
        "application": "batch",
        "environment": "prod",
        "owner": "platform-batch",
        "cost_center": "cc-4400",
        "patch_group": "linux-prod-standard",
        "backup_tier": "silver",
        "subnet_id": "subnet-private-batch-b",
        "availability_zone": "us-east-1b",
        "private_ip": "10.42.24.99",
        "instance_type": "m7i.large",
        "target_ami_id": "ami-linux-batch-20260601",
        "security_group_ids": ["sg-batch-helper", "sg-ssm-egress", "sg-vpc-dns"],
        "root_gib": 40,
    }
    disks["batch-helper"] = [
        {
            "device_name": "/dev/sdf",
            "snapshot_id": "snap-batch-helper-20260601",
            "size_gib": 50,
            "volume_role": "scratch",
            "iops": 3000,
            "throughput": 125,
        }
    ]
    deps["batch-helper"] = ["claims-worker"]
    windows["batch-helper"] = {
        "legacy_instance_id": "i-0winbat001",
        "writer_role": "worker",
        "dns_name": "batch-helper.internal.claims",
    }
    maint["assignments"]["batch-helper"] = "wave-b"
    checksums["batch-helper:root"] = wave_lab.sha256_bytes(
        wave_lab.root_payload("batch-helper")
    )
    checksums["batch-helper:/dev/sdf"] = wave_lab.sha256_bytes(
        wave_lab.snapshot_payload(
            "batch-helper", "scratch", "snap-batch-helper-20260601"
        )
    )

    _reset_data(
        {
            "cmdb.json": cmdb,
            "disks.json": disks,
            "dependencies.json": deps,
            "windows.json": windows,
            "maintenance.json": maint,
            "checksums.json": checksums,
        }
    )
    workspace = submission_dir / "workspaces" / "wave"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = wave_lab.run_rehearsal(plan)
    assert report["status"] == "READY", report
    handoffs = {h["workload"]: h for h in report["handoffs"]}
    assert handoffs["batch-helper"]["writer"] == "linux"
    assert report["wave_order"].index("claims-worker") < report["wave_order"].index(
        "batch-helper"
    )


def test_idempotent_digest_matches_agent(agent_report: dict, baseline: tuple[dict, dict]) -> None:
    """Verifier digest for READY baseline must match the agent report digest."""
    _plan, report = baseline
    assert report["report_digest"] == agent_report["report_digest"]


def test_artifacts_present() -> None:
    """Required cutover artifacts must exist under /app/output and /app/var/wave."""
    assert (OUTPUT_ARTIFACT / "rehearsal-report.json").is_file()
    assert (OUTPUT_ARTIFACT / "cutover-journal.json").is_file()
    assert (VAR_ARTIFACT / "plan.json").is_file() or (VAR_ARTIFACT / "tfplan").exists()
    assert TERRAFORM_ARTIFACT.is_dir()


def test_weak_tls_style_imds_counterexample(submission_dir: Path) -> None:
    """Plans missing required IMDS tokens fail closed in the lab policy gate."""
    _reset_data()
    workspace = submission_dir / "workspaces" / "wave"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    graph = wave_lab.normalize_plan(plan)
    # mutate one instance to optional tokens
    wl = next(iter(graph["instances"]))
    graph["instances"][wl]["metadata_http_tokens"] = "optional"
    errors = wave_lab.plan_policy_errors(
        graph,
        _load_base("cmdb.json"),
        _load_base("disks.json"),
        _load_base("defaults.json"),
    )
    assert any("IMDS" in e for e in errors)
