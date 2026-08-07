"""Verifier for the fenced EC2 fleet rollout.

Replans submitted Terraform, rebuilds the submitted Go controller against a
verifier-owned control plane, and checks provenance, placement, rollout
fencing, volume generations, import moves, drift, journal repair, hidden
inventory variations, and anti-cheat mismatches.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONTROLLER = Path("/app/controller")
TERRAFORM = Path("/app/terraform")
CMD = Path("/app/cmd")
OUTPUT = Path("/app/output")
VAR = Path("/app/var/fleet")
BIN = Path("/app/bin/fenced-fleet-rollout")
GO_MOD = Path("/app/go.mod")
BASE_CONFIG = FIXTURES / "data" / "fleet_config.json"
WORK_CONFIG = Path("/app/data/fleet_config.json")
CP_URL = "http://127.0.0.1:18080"

ENV = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
    "TF_IN_AUTOMATION": "1",
    "CHECKPOINT_DISABLE": "1",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
    "FLEET_CONTROL_PLANE": CP_URL,
    "FLEET_CONFIG": str(WORK_CONFIG),
}

FIELDS = (
    "manifest_version",
    "ami_id",
    "ami_owner_account_id",
    "architecture",
    "commit_sha",
    "build_id",
    "user_data_sha256",
)


def _run(cmd, cwd=None, check=False):
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=ENV,
        text=True,
        capture_output=True,
        check=check,
    )


def _load_config():
    return json.loads(BASE_CONFIG.read_text(encoding="utf-8"))


def _write_config(cfg):
    WORK_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    WORK_CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def _manifest_digest(artifact):
    payload = {k: artifact[k] for k in FIELDS}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _next_release(cfg, suffix="19"):
    value = copy.deepcopy(cfg)
    artifact = value["release_artifact"]
    artifact.update(
        {
            "ami_id": f"ami-0feed202606{suffix}",
            "commit_sha": f"commit-{suffix}-abcdef",
            "build_id": f"build-202606{suffix}.1",
            "user_data_sha256": suffix[0] * 64,
        }
    )
    value["ami_catalog"]["images"][artifact["ami_id"]] = {
        "owner_account_id": artifact["ami_owner_account_id"],
        "architecture": artifact["architecture"],
        "state": "available",
        "deprecated": False,
    }
    artifact["manifest_sha256"] = _manifest_digest(artifact)
    return value


def _reset_workspace():
    if VAR.exists():
        shutil.rmtree(VAR)
    VAR.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = Path("/app/data")
    if data.exists():
        shutil.rmtree(data)
    shutil.copytree(FIXTURES / "data", data)


def _ensure_sources():
    assert CONTROLLER.exists(), "controller artifact missing"
    assert TERRAFORM.exists(), "terraform artifact missing"
    assert (CMD / "fleetctl" / "main.go").exists(), "fleetctl source missing"
    assert GO_MOD.exists(), "go.mod missing"
    assert BIN.exists(), "operator binary missing"


def _build_fleetctl():
    out = Path("/tmp/fleetctl-verifier")
    proc = _run(["go", "build", "-o", str(out), "./cmd/fleetctl"], cwd=Path("/app"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return out


def _start_cp():
    proc = subprocess.Popen(
        [
            "/opt/ec2-controlplane",
            "-listen",
            "127.0.0.1:18080",
            "-state",
            str(VAR / "controlplane-state.json"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        env=ENV,
    )
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(CP_URL + "/healthz", timeout=1) as resp:
                if resp.status == 200:
                    return proc
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    proc.kill()
    raise AssertionError("control plane failed to start")


def _stop_cp(proc):
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _inventory():
    with urllib.request.urlopen(CP_URL + "/v1/inventory", timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fleetctl(fleetctl, command, cfg, prior=None, state=None, journal=None):
    cfg_path = VAR / "cfg.json"
    out_path = VAR / "out.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    args = [
        str(fleetctl),
        command,
        "--config",
        str(cfg_path),
        "--out",
        str(out_path),
        "--control-plane",
        CP_URL,
    ]
    if prior is not None:
        prior_path = VAR / "prior.json"
        prior_path.write_text(json.dumps(prior), encoding="utf-8")
        args += ["--prior-state", str(prior_path)]
    if state is not None:
        args += ["--state", str(state)]
    if journal is not None:
        args += ["--journal", str(journal)]
    proc = _run(args)
    payload = (
        json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    )
    return proc, payload


def _plan_terraform(config_path):
    workspace = TERRAFORM / "workspaces" / "fleet"
    init = _run(["terraform", "init", "-backend=false", "-input=false"], cwd=workspace)
    assert init.returncode == 0, init.stdout + init.stderr
    plan_path = VAR / "hidden.tfplan"
    plan = _run(
        [
            "terraform",
            "plan",
            "-refresh=false",
            "-input=false",
            f"-out={plan_path}",
            f"-var=config_path={config_path}",
        ],
        cwd=workspace,
    )
    assert plan.returncode == 0, plan.stdout + plan.stderr
    show = _run(["terraform", "show", "-json", str(plan_path)], cwd=workspace)
    assert show.returncode == 0, show.stdout + show.stderr
    return json.loads(show.stdout)


def _module_values(plan):
    planned = plan.get("planned_values", {}).get("root_module", {})
    modules = planned.get("child_modules") or []
    result = {}
    for mod in modules:
        for r in mod.get("resources", []):
            result[r["address"]] = r
    return result


def _first_resource(plan, type_name):
    for resource in _module_values(plan).values():
        if resource.get("type") == type_name:
            return resource.get("values") or {}
    raise AssertionError(f"{type_name} missing from plan")


def _ebs_volumes(plan):
    return [
        r.get("values") or {}
        for r in _module_values(plan).values()
        if r.get("type") == "aws_ebs_volume"
    ]


def _moved_blocks():
    text = (TERRAFORM / "modules" / "fleet" / "state_migrations.tf").read_text(
        encoding="utf-8"
    )
    moves = set()
    current_from = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("from"):
            current_from = stripped.split("=", 1)[1].strip()
        elif stripped.startswith("to") and current_from:
            moves.add((current_from, stripped.split("=", 1)[1].strip()))
            current_from = None
    return moves


@pytest.fixture(scope="module")
def artifacts_present():
    _ensure_sources()


@pytest.fixture()
def clean_env(artifacts_present):
    _reset_workspace()
    yield
    _run(["pkill", "-f", "ec2-controlplane"], check=False)


class TestArtifactIntegrity:
    def test_required_artifacts_exist(self, artifacts_present):
        """Submitted controller, Terraform, fleetctl, and operator artifacts are present."""
        assert (CONTROLLER / "rollout.go").exists()
        assert (TERRAFORM / "modules" / "fleet" / "main.tf").exists()
        assert (CMD / "fleetctl" / "main.go").exists()


class TestVisibleHappyPath:
    def test_operator_reaches_ready_with_matching_control_plane(self, clean_env):
        """Public operator plans Terraform, applies via control plane, and reports READY."""
        proc = _run([str(BIN)])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        report = json.loads(
            (OUTPUT / "rollout-report.json").read_text(encoding="utf-8")
        )
        assert report["status"] == "READY"
        assert report["instance_count"] == report["control_plane_instance_count"]
        assert report["volume_count"] == report["control_plane_volume_count"]
        assert report["state_digest"] == report["control_plane_state_digest"]
        assert (VAR / "plan.json").exists()

    def test_second_run_keeps_report_digest(self, clean_env):
        """Identical rerun is idempotent on report_digest."""
        first = _run([str(BIN)])
        assert first.returncode == 0, first.stdout + first.stderr
        digest1 = json.loads((OUTPUT / "rollout-report.json").read_text())[
            "report_digest"
        ]
        second = _run([str(BIN)])
        assert second.returncode == 0, second.stdout + second.stderr
        digest2 = json.loads((OUTPUT / "rollout-report.json").read_text())[
            "report_digest"
        ]
        assert digest1 == digest2


class TestTerraformSemantics:
    def test_launch_template_uses_approved_ami_and_imdsv2(self, clean_env):
        """Planned launch template pins the approved AMI and requires IMDSv2."""
        cfg = _load_config()
        plan = _plan_terraform(WORK_CONFIG)
        lt = _first_resource(plan, "aws_launch_template")
        assert lt.get("image_id") == cfg["release_artifact"]["ami_id"]
        assert lt.get("image_id") != cfg["ami_catalog"]["latest"]
        meta = (lt.get("metadata_options") or [{}])[0]
        assert meta.get("http_tokens") == "required"
        assert meta.get("http_put_response_hop_limit") == 1

    def test_iam_policy_is_least_privilege(self, clean_env):
        """Planned IAM policy exposes only the four documented statement Sids."""
        plan = _plan_terraform(WORK_CONFIG)
        policy_raw = _first_resource(plan, "aws_iam_role_policy").get("policy")
        policy = json.loads(policy_raw) if isinstance(policy_raw, str) else (policy_raw or {})
        statements = {s["Sid"]: s for s in policy.get("Statement", [])}
        assert set(statements) == {
            "SsmControlPlane",
            "ReadReleaseArtifact",
            "DecryptDataVolume",
            "PublishPaymentsMetrics",
        }
        assert statements["SsmControlPlane"]["Action"] != ["*"]

    def test_security_group_is_alb_scoped(self, clean_env):
        """Planned security group admits ALB service traffic rather than open SSH."""
        cfg = _load_config()
        plan = _plan_terraform(WORK_CONFIG)
        sg = _first_resource(plan, "aws_security_group")
        ingress = sg.get("ingress") or []
        assert any(
            rule.get("from_port") == cfg["service_port"]
            and rule.get("to_port") == cfg["service_port"]
            for rule in ingress
        )
        assert not any(
            rule.get("from_port") == 22 and "0.0.0.0/0" in (rule.get("cidr_blocks") or [])
            for rule in ingress
        )

    def test_volumes_are_encrypted(self, clean_env):
        """Planned EBS volumes are encrypted with configured KMS material."""
        plan = _plan_terraform(WORK_CONFIG)
        volumes = _ebs_volumes(plan)
        assert volumes
        assert all(v.get("encrypted") is True for v in volumes)

    def test_state_migrations_declare_required_moves(self, clean_env):
        """state_migrations.tf declares the legacy-to-canonical moved addresses."""
        expected = {
            ("aws_launch_template.payments", "aws_launch_template.this"),
            ("aws_autoscaling_group.payments", "aws_autoscaling_group.this"),
            ("aws_security_group.payments_instance", "aws_security_group.instance"),
            ("aws_iam_role.payments_instance", "aws_iam_role.instance"),
            ("aws_ebs_volume.payments_data", "aws_ebs_volume.data"),
            ("aws_volume_attachment.payments_data", "aws_volume_attachment.data"),
        }
        assert expected.issubset(_moved_blocks())


class TestControllerBehavior:
    def test_release_provenance_and_stable_slots(self, clean_env):
        """Controller apply commits approved provenance and stable integer slots."""
        cfg = _load_config()
        fleetctl = _build_fleetctl()
        cp = _start_cp()
        try:
            proc, state = _fleetctl(
                fleetctl, "apply", cfg, state=VAR / "state.json", journal=VAR / "journal.jsonl"
            )
            assert proc.returncode == 0, proc.stdout + proc.stderr
            assert state["release_identity"]["ami_id"] == cfg["release_artifact"]["ami_id"]
            assert state["launch_template"]["provenance"] == {
                "commit_sha": cfg["release_artifact"]["commit_sha"],
                "build_id": cfg["release_artifact"]["build_id"],
                "manifest_sha256": cfg["release_artifact"]["manifest_sha256"],
            }
            slots = [i["slot"] for i in state["instances"]]
            assert slots == list(range(cfg["asg"]["desired_capacity"]))
            inv = _inventory()
            assert inv["state_digest"] == state["state_digest"]
        finally:
            _stop_cp(cp)

    def test_pilot_wave_rollout_and_volume_generation(self, clean_env):
        """Release change completes pilot-then-wave events and bumps attachment generation once."""
        cfg = _load_config()
        fleetctl = _build_fleetctl()
        cp = _start_cp()
        try:
            _, baseline = _fleetctl(
                fleetctl, "apply", cfg, state=VAR / "state.json", journal=VAR / "journal.jsonl"
            )
            nxt = _next_release(cfg)
            proc, rolled = _fleetctl(
                fleetctl,
                "apply",
                nxt,
                prior=baseline,
                state=VAR / "state.json",
                journal=VAR / "journal.jsonl",
            )
            assert proc.returncode == 0, proc.stdout + proc.stderr
            refresh = rolled["autoscaling_group"]["instance_refresh"]
            assert refresh["status"] == "completed"
            events = [e["event"] for e in refresh["events"]]
            assert events[0:3] == ["pilot_launched", "pilot_healthy", "pilot_committed"]
            assert events[-1] == "rollout_completed"
            assert all(v["attachment_generation"] == 2 for v in rolled["ebs_volumes"])
        finally:
            _stop_cp(cp)

    def test_pilot_failure_preserves_prior_fleet(self, clean_env):
        """Failed pilot health rolls back without committing replacements."""
        cfg = _load_config()
        fleetctl = _build_fleetctl()
        cp = _start_cp()
        try:
            _, baseline = _fleetctl(
                fleetctl, "apply", cfg, state=VAR / "state.json", journal=VAR / "journal.jsonl"
            )
            nxt = _next_release(cfg)
            nxt["rollout"]["candidate_health"] = "fail_pilot"
            proc, rolled = _fleetctl(
                fleetctl,
                "apply",
                nxt,
                prior=baseline,
                state=VAR / "state2.json",
                journal=VAR / "journal2.jsonl",
            )
            assert proc.returncode == 0, proc.stdout + proc.stderr
            assert rolled["autoscaling_group"]["instance_refresh"]["status"] == "rolled_back"
            assert [i["id"] for i in rolled["instances"]] == [
                i["id"] for i in baseline["instances"]
            ]
        finally:
            _stop_cp(cp)

    def test_lost_response_resume_is_idempotent(self, clean_env):
        """Lost reply after pilot commit resumes without duplicate identities."""
        cfg = _load_config()
        fleetctl = _build_fleetctl()
        cp = _start_cp()
        try:
            _, baseline = _fleetctl(
                fleetctl, "apply", cfg, state=VAR / "state.json", journal=VAR / "journal.jsonl"
            )
            nxt = _next_release(cfg)
            nxt["rollout"]["fault_point"] = "after_pilot_commit_response_lost"
            proc, partial = _fleetctl(
                fleetctl,
                "apply",
                nxt,
                prior=baseline,
                state=VAR / "state.json",
                journal=VAR / "journal.jsonl",
            )
            assert proc.returncode == 3
            assert partial["control_plane_response_lost"] is True
            nxt["rollout"]["fault_point"] = "none"
            proc2, done = _fleetctl(
                fleetctl,
                "apply",
                nxt,
                prior=partial,
                state=VAR / "state.json",
                journal=VAR / "journal.jsonl",
            )
            assert proc2.returncode == 0, proc2.stdout + proc2.stderr
            assert done["autoscaling_group"]["instance_refresh"]["status"] == "completed"
            ids = [i["id"] for i in done["instances"]]
            assert len(ids) == len(set(ids))
        finally:
            _stop_cp(cp)

    def test_stale_owner_is_rejected(self, clean_env):
        """A different owner token cannot resume an in-progress operation."""
        cfg = _load_config()
        fleetctl = _build_fleetctl()
        cp = _start_cp()
        try:
            _, baseline = _fleetctl(
                fleetctl, "apply", cfg, state=VAR / "state.json", journal=VAR / "journal.jsonl"
            )
            nxt = _next_release(cfg)
            nxt["rollout"]["fault_point"] = "after_pilot_commit_response_lost"
            _, partial = _fleetctl(
                fleetctl,
                "apply",
                nxt,
                prior=baseline,
                state=VAR / "state.json",
                journal=VAR / "journal.jsonl",
            )
            nxt["rollout"]["fault_point"] = "none"
            nxt["rollout"]["owner_token"] = "intruder"
            proc, payload = _fleetctl(
                fleetctl,
                "apply",
                nxt,
                prior=partial,
                state=VAR / "state-bad.json",
                journal=VAR / "journal-bad.jsonl",
            )
            assert proc.returncode == 2
            assert "stale rollout owner" in str(payload.get("error", ""))
        finally:
            _stop_cp(cp)

    def test_subnet_reorder_preserves_placement(self, clean_env):
        """Reordering subnet inputs does not move already placed slots."""
        cfg = _load_config()
        fleetctl = _build_fleetctl()
        cp = _start_cp()
        try:
            _, baseline = _fleetctl(
                fleetctl, "apply", cfg, state=VAR / "state.json", journal=VAR / "journal.jsonl"
            )
            reordered = copy.deepcopy(cfg)
            reordered["placement"]["subnets"] = list(
                reversed(reordered["placement"]["subnets"])
            )
            proc, again = _fleetctl(fleetctl, "plan", reordered, prior=baseline)
            assert proc.returncode == 0, proc.stdout + proc.stderr
            assert [i["subnet_id"] for i in again["instances"]] == [
                i["subnet_id"] for i in baseline["instances"]
            ]
        finally:
            _stop_cp(cp)

    def test_invalid_manifest_fails_closed(self, clean_env):
        """Broken release digest fails validation before mutation."""
        cfg = _load_config()
        cfg["release_artifact"]["manifest_sha256"] = "0" * 64
        fleetctl = _build_fleetctl()
        proc, payload = _fleetctl(fleetctl, "validate", cfg)
        assert proc.returncode == 2
        assert "manifest_sha256" in str(payload.get("error", ""))

    def test_torn_journal_tail_is_repaired(self, clean_env):
        """Invalid final journal line is truncated while valid records remain."""
        cfg = _load_config()
        fleetctl = _build_fleetctl()
        journal = VAR / "torn.jsonl"
        journal.write_text(
            json.dumps(
                {
                    "operation_id": "op-1",
                    "release_manifest_sha256": "a",
                    "refresh_status": "stable",
                    "state_digest": "d",
                }
            )
            + "\n{not-json\n",
            encoding="utf-8",
        )
        cp = _start_cp()
        try:
            proc, state = _fleetctl(
                fleetctl, "apply", cfg, state=VAR / "state.json", journal=journal
            )
            assert proc.returncode == 0, proc.stdout + proc.stderr
            assert state["journal_repair"]["truncated_tail"] is True
            lines = [
                ln for ln in journal.read_text(encoding="utf-8").splitlines() if ln.strip()
            ]
            assert len(lines) >= 2
            assert all(json.loads(ln) for ln in lines)
        finally:
            _stop_cp(cp)

    def test_report_only_drift_does_not_replace(self, clean_env):
        """Manual instance drift is reported without rolling replacement."""
        cfg = _load_config()
        fleetctl = _build_fleetctl()
        cp = _start_cp()
        try:
            _, baseline = _fleetctl(
                fleetctl, "apply", cfg, state=VAR / "state.json", journal=VAR / "journal.jsonl"
            )
            drifted = copy.deepcopy(baseline)
            drifted["instances"][0]["public_ip_associated"] = True
            proc, state = _fleetctl(fleetctl, "plan", cfg, prior=drifted)
            assert proc.returncode == 0, proc.stdout + proc.stderr
            assert state["autoscaling_group"]["instance_refresh"]["status"] == "stable"
            assert any(d.get("action") == "report_only" for d in state["drift_report"])
            assert not any(
                a.get("action") == "rolling_replace" for a in state["plan_actions"]
            )
        finally:
            _stop_cp(cp)


class TestHiddenVariations:
    def test_odd_fleet_and_expanded_subnet(self, clean_env):
        """Odd desired capacity with an added AZ still balances private placements."""
        cfg = _load_config()
        cfg["asg"]["desired_capacity"] = 5
        cfg["asg"]["min_size"] = 3
        cfg["asg"]["max_size"] = 8
        cfg["placement"]["subnets"].append(
            {
                "account_id": cfg["account_id"],
                "az": "us-east-1d",
                "id": "subnet-app-d",
                "tier": "private_app",
            }
        )
        _write_config(cfg)
        fleetctl = _build_fleetctl()
        cp = _start_cp()
        try:
            proc, state = _fleetctl(
                fleetctl, "apply", cfg, state=VAR / "state.json", journal=VAR / "journal.jsonl"
            )
            assert proc.returncode == 0, proc.stdout + proc.stderr
            assert len(state["instances"]) == 5
            assert all(not i["public_ip_associated"] for i in state["instances"])
        finally:
            _stop_cp(cp)

    def test_reordered_manifest_fields_keep_identities(self, clean_env):
        """Key reordering in release_artifact does not change template version."""
        cfg = _load_config()
        fleetctl = _build_fleetctl()
        _, a = _fleetctl(fleetctl, "plan", cfg)
        shuffled = copy.deepcopy(cfg)
        artifact = shuffled["release_artifact"]
        shuffled["release_artifact"] = {
            "user_data_sha256": artifact["user_data_sha256"],
            "manifest_version": artifact["manifest_version"],
            "architecture": artifact["architecture"],
            "ami_owner_account_id": artifact["ami_owner_account_id"],
            "build_id": artifact["build_id"],
            "commit_sha": artifact["commit_sha"],
            "ami_id": artifact["ami_id"],
            "manifest_sha256": artifact["manifest_sha256"],
        }
        _, b = _fleetctl(fleetctl, "plan", shuffled)
        assert a["launch_template"]["version"] == b["launch_template"]["version"]
        assert a["state_digest"] == b["state_digest"]


class TestAntiCheat:
    def test_forged_report_is_overwritten_or_rejected(self, clean_env):
        """Forged READY output without control-plane agreement cannot survive a real run."""
        forged = {
            "status": "READY",
            "report_digest": "deadbeef",
            "state_digest": "local-only",
            "control_plane_state_digest": "other",
            "instance_count": 6,
            "control_plane_instance_count": 0,
            "volume_count": 6,
            "control_plane_volume_count": 0,
            "refresh_status": "stable",
            "operation_id": "forged",
        }
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / "rollout-report.json").write_text(
            json.dumps(forged, indent=2) + "\n", encoding="utf-8"
        )
        proc = _run([str(BIN)])
        if proc.returncode == 0:
            report = json.loads((OUTPUT / "rollout-report.json").read_text())
            assert report["state_digest"] == report["control_plane_state_digest"]
            assert report["status"] == "READY"
            assert report["report_digest"] != "deadbeef"
        else:
            assert proc.returncode != 0
