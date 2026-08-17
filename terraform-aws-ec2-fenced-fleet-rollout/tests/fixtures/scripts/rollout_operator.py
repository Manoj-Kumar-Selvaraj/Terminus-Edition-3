#!/usr/bin/env python3
"""Plan Terraform, drive the fenced fleet controller against the control plane."""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WORKSPACE = Path("/app/terraform/workspaces/fleet")
VAR = Path("/app/var/fleet")
OUTPUT = Path("/app/output")
CONFIG = Path(os.environ.get("FLEET_CONFIG", "/app/data/fleet_config.json"))
CONTROLPLANE_BIN = Path("/opt/ec2-controlplane")
FLEETCTL_SRC = Path("/app")
CP_URL = os.environ.get("FLEET_CONTROL_PLANE", "http://127.0.0.1:18080")
EXPECTED_CP_HASH = Path("/opt/ec2-controlplane.sha256")


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
        "TF_IN_AUTOMATION": "1",
        "CHECKPOINT_DISABLE": "1",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_DEFAULT_REGION": "us-east-1",
        "FLEET_CONTROL_PLANE": CP_URL,
    }
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, text=True, capture_output=True)
    if check and proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(proc.returncode)
    return proc


def verify_controlplane_hash() -> None:
    raw = CONTROLPLANE_BIN.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected = EXPECTED_CP_HASH.read_text(encoding="utf-8").strip().split()[0]
    if digest != expected:
        raise SystemExit(f"control plane binary hash mismatch: {digest} != {expected}")


def wait_health(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url + "/healthz", timeout=1) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    raise SystemExit("control plane failed to become healthy")


def start_controlplane() -> subprocess.Popen:
    VAR.mkdir(parents=True, exist_ok=True)
    verify_controlplane_hash()
    proc = subprocess.Popen(
        [
            str(CONTROLPLANE_BIN),
            "-listen",
            "127.0.0.1:18080",
            "-state",
            str(VAR / "controlplane-state.json"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_health(CP_URL)
    except SystemExit:
        proc.kill()
        raise
    return proc


def build_fleetctl() -> Path:
    out = Path("/tmp/fleetctl")
    proc = run(["go", "build", "-o", str(out), "./cmd/fleetctl"], cwd=FLEETCTL_SRC, check=False)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(proc.returncode)
    return out


def terraform_plan() -> dict:
    VAR.mkdir(parents=True, exist_ok=True)
    run(["terraform", "init", "-backend=false", "-input=false"], cwd=WORKSPACE)
    run(["terraform", "validate"], cwd=WORKSPACE)
    plan_path = VAR / "tfplan"
    run(
        [
            "terraform",
            "plan",
            "-refresh=false",
            "-input=false",
            f"-out={plan_path}",
            f"-var=config_path={CONFIG}",
        ],
        cwd=WORKSPACE,
    )
    show = run(["terraform", "show", "-json", str(plan_path)], cwd=WORKSPACE)
    plan = json.loads(show.stdout)
    (VAR / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan


def inventory() -> dict:
    with urllib.request.urlopen(CP_URL + "/v1/inventory", timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def report_digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    VAR.mkdir(parents=True, exist_ok=True)
    plan = terraform_plan()
    cp = start_controlplane()
    try:
        fleetctl = build_fleetctl()
        state_path = VAR / "ec2_state.json"
        journal_path = VAR / "ec2_state.json.journal.jsonl"
        out_path = VAR / "apply-result.json"
        apply = run(
            [
                str(fleetctl),
                "apply",
                "--config",
                str(CONFIG),
                "--state",
                str(state_path),
                "--journal",
                str(journal_path),
                "--out",
                str(out_path),
                "--control-plane",
                CP_URL,
            ],
            check=False,
        )
        if apply.returncode not in (0, 3):
            sys.stderr.write(apply.stdout + apply.stderr)
            return apply.returncode
        result = json.loads(out_path.read_text(encoding="utf-8"))
        inv = inventory()
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        desired = int((cfg.get("asg") or {}).get("desired_capacity") or 0)
        approved_ami = (cfg.get("release_artifact") or {}).get("ami_id")
        latest_alias = ((cfg.get("ami_catalog") or {}).get("latest"))
        refresh_status = (
            result.get("autoscaling_group", {})
            .get("instance_refresh", {})
            .get("status")
        )
        release_ami = (result.get("release_identity") or {}).get("ami_id")
        template_ami = (result.get("launch_template") or {}).get("ami_id")
        payload = {
            "status": "PARTIAL",
            "application": cfg.get("app"),
            "environment": cfg.get("environment"),
            "release_manifest_sha256": result.get("release_identity", {}).get(
                "manifest_sha256"
            ),
            "launch_template_version": result.get("launch_template", {}).get("version"),
            "instance_count": len(result.get("instances", [])),
            "volume_count": len(result.get("ebs_volumes", [])),
            "refresh_status": refresh_status,
            "operation_id": result.get("outputs", {}).get("rollout_operation_id"),
            "control_plane_instance_count": len(inv.get("instances", [])),
            "control_plane_volume_count": len(inv.get("ebs_volumes", [])),
            "plan_resource_count": len((plan.get("resource_changes") or [])),
            "state_digest": result.get("state_digest"),
            "control_plane_state_digest": inv.get("state_digest"),
        }
        ready = (
            apply.returncode == 0
            and refresh_status in {"stable", "completed"}
            and payload["instance_count"] == desired
            and payload["volume_count"] == desired * len(cfg.get("ebs_volumes") or [])
            and payload["instance_count"] == payload["control_plane_instance_count"]
            and payload["volume_count"] == payload["control_plane_volume_count"]
            and payload["state_digest"]
            and payload["state_digest"] == payload["control_plane_state_digest"]
            and release_ami == approved_ami
            and template_ami == approved_ami
            and template_ami != latest_alias
            and (result.get("launch_template") or {})
            .get("metadata_options", {})
            .get("http_tokens")
            == "required"
        )
        payload["status"] = "READY" if ready else "MISMATCH"
        stable = {
            "status": payload["status"],
            "application": payload["application"],
            "environment": payload["environment"],
            "release_manifest_sha256": payload["release_manifest_sha256"],
            "launch_template_version": payload["launch_template_version"],
            "instance_count": payload["instance_count"],
            "volume_count": payload["volume_count"],
            "refresh_status": payload["refresh_status"],
            "control_plane_instance_count": payload["control_plane_instance_count"],
            "control_plane_volume_count": payload["control_plane_volume_count"],
        }
        payload["report_digest"] = report_digest(stable)
        (OUTPUT / "rollout-report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": payload["status"], "digest": payload["report_digest"]}))
        return 0 if payload["status"] == "READY" else 1
    finally:
        cp.send_signal(signal.SIGTERM)
        try:
            cp.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cp.kill()


if __name__ == "__main__":
    raise SystemExit(main())
