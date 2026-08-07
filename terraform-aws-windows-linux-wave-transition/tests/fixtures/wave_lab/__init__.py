"""Local wave rehearsal lab for Windows→Linux EC2 cutover."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

def _data_dir() -> Path:
    return Path(os.environ.get("WAVE_DATA_DIR", "/app/data"))


def _var_dir() -> Path:
    return Path(os.environ.get("WAVE_VAR_DIR", "/app/var/wave"))


def _output_dir() -> Path:
    return Path(os.environ.get("WAVE_OUTPUT_DIR", "/app/output"))


def _load(name: str) -> Any:
    return json.loads((_data_dir() / name).read_text(encoding="utf-8"))


def snapshot_payload(workload: str, volume_role: str, snapshot_id: str) -> bytes:
    return f"{workload}:{volume_role}:{snapshot_id}\n".encode()


def root_payload(workload: str) -> bytes:
    return f"{workload}:root:seed\n".encode()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_plan(plan: dict) -> dict:
    """Extract semantic instance/volume/attachment graph from a TF plan."""
    changes = plan.get("resource_changes") or []
    instances: dict[str, dict] = {}
    volumes: dict[str, dict] = {}
    attachments: list[dict] = []

    for rc in changes:
        rtype = rc.get("type")
        after = (rc.get("change") or {}).get("after") or {}
        actions = (rc.get("change") or {}).get("actions") or []
        if "create" not in actions and "update" not in actions:
            continue
        if rtype == "aws_instance":
            tags = after.get("tags") or after.get("tags_all") or {}
            wl = tags.get("Workload") or tags.get("Name")
            if not wl:
                continue
            md = after.get("metadata_options") or {}
            if isinstance(md, list):
                md = md[0] if md else {}
            root = after.get("root_block_device") or {}
            if isinstance(root, list):
                root = root[0] if root else {}
            instances[wl] = {
                "ami": after.get("ami"),
                "instance_type": after.get("instance_type"),
                "subnet_id": after.get("subnet_id"),
                "private_ip": after.get("private_ip"),
                "availability_zone": after.get("availability_zone"),
                "vpc_security_group_ids": list(after.get("vpc_security_group_ids") or []),
                "iam_instance_profile": after.get("iam_instance_profile"),
                "associate_public_ip_address": after.get("associate_public_ip_address"),
                "disable_api_termination": after.get("disable_api_termination"),
                "monitoring": after.get("monitoring"),
                "ebs_optimized": after.get("ebs_optimized"),
                "key_name": after.get("key_name"),
                "metadata_http_tokens": md.get("http_tokens"),
                "metadata_hop_limit": md.get("http_put_response_hop_limit"),
                "root_encrypted": root.get("encrypted"),
                "root_kms_key_id": root.get("kms_key_id"),
                "root_volume_size": root.get("volume_size"),
                "tags": dict(tags),
            }
        elif rtype == "aws_ebs_volume":
            tags = after.get("tags") or after.get("tags_all") or {}
            wl = tags.get("Workload")
            device = tags.get("DeviceName")
            key = f"{wl}:{device}" if wl and device else rc.get("address", "")
            volumes[key] = {
                "workload": wl,
                "device_name": device,
                "availability_zone": after.get("availability_zone"),
                "size": after.get("size"),
                "type": after.get("type"),
                "iops": after.get("iops"),
                "throughput": after.get("throughput"),
                "encrypted": after.get("encrypted"),
                "kms_key_id": after.get("kms_key_id"),
                "snapshot_id": after.get("snapshot_id"),
                "volume_role": tags.get("VolumeRole"),
                "tags": dict(tags),
                "address": rc.get("address"),
            }
        elif rtype == "aws_volume_attachment":
            attachments.append(
                {
                    "device_name": after.get("device_name"),
                    "volume_id": after.get("volume_id"),
                    "instance_id": after.get("instance_id"),
                    "force_detach": after.get("force_detach"),
                    "address": rc.get("address"),
                }
            )

    return {
        "instances": instances,
        "volumes": volumes,
        "attachments": attachments,
    }


def plan_policy_errors(graph: dict, cmdb: dict, disks: dict, defaults: dict) -> list[str]:
    errors: list[str] = []
    forbidden = set(defaults.get("forbidden_admin_groups") or [])
    required_ssm = defaults.get("required_ssm_security_group")
    kms = defaults.get("kms_key_id")
    profile = defaults.get("iam_instance_profile")

    for wl, record in cmdb.items():
        inst = graph["instances"].get(wl)
        if not inst:
            errors.append(f"missing instance for {wl}")
            continue
        if inst["ami"] != record["target_ami_id"]:
            errors.append(f"{wl}: ami mismatch")
        if inst["instance_type"] != record["instance_type"]:
            errors.append(f"{wl}: instance_type mismatch")
        if inst["subnet_id"] != record["subnet_id"]:
            errors.append(f"{wl}: subnet mismatch")
        if inst["private_ip"] != record["private_ip"]:
            errors.append(f"{wl}: private_ip mismatch")
        if inst["availability_zone"] != record["availability_zone"]:
            errors.append(f"{wl}: az mismatch")
        sgs = set(inst["vpc_security_group_ids"])
        if sgs & forbidden:
            errors.append(f"{wl}: forbidden admin groups present")
        if required_ssm and required_ssm not in sgs:
            errors.append(f"{wl}: missing required SSM security group")
        if inst["iam_instance_profile"] != profile:
            errors.append(f"{wl}: wrong instance profile")
        if inst["associate_public_ip_address"] is not False:
            errors.append(f"{wl}: public IP association must be false")
        if inst["disable_api_termination"] is not True:
            errors.append(f"{wl}: termination protection required")
        if inst["metadata_http_tokens"] != defaults.get("metadata_http_tokens"):
            errors.append(f"{wl}: IMDS tokens must be required")
        if inst.get("metadata_hop_limit") != defaults.get("metadata_hop_limit"):
            errors.append(f"{wl}: IMDS hop limit mismatch")
        if inst["root_encrypted"] is not True:
            errors.append(f"{wl}: root must be encrypted")
        if inst["root_kms_key_id"] != kms:
            errors.append(f"{wl}: root kms mismatch")
        if inst["key_name"]:
            errors.append(f"{wl}: key_name must be omitted")

        expected_vols = disks.get(wl) or []
        for vol in expected_vols:
            key = f"{wl}:{vol['device_name']}"
            planned = graph["volumes"].get(key)
            if not planned:
                errors.append(f"missing volume {key}")
                continue
            if planned["snapshot_id"] != vol["snapshot_id"]:
                errors.append(f"{key}: snapshot mismatch")
            if planned["size"] != vol["size_gib"]:
                errors.append(f"{key}: size mismatch")
            if planned["type"] != "gp3":
                errors.append(f"{key}: type must be gp3")
            if planned["encrypted"] is not True:
                errors.append(f"{key}: must be encrypted")
            if planned["kms_key_id"] != kms:
                errors.append(f"{key}: kms mismatch")
            if planned["availability_zone"] != record["availability_zone"]:
                errors.append(f"{key}: az mismatch")
            if planned["iops"] != vol["iops"]:
                errors.append(f"{key}: iops mismatch")
            if planned["throughput"] != vol["throughput"]:
                errors.append(f"{key}: throughput mismatch")

    attach_devices = {a["device_name"] for a in graph["attachments"]}
    for wl, vols in disks.items():
        for vol in vols:
            if vol["device_name"] not in attach_devices:
                # attachment device_name is enough; volume_id may be unknown ref
                pass
    expected_attach = sum(len(v) for v in disks.values())
    if len(graph["attachments"]) < expected_attach:
        errors.append("missing volume attachments")
    for a in graph["attachments"]:
        if a.get("force_detach") is True:
            errors.append("force_detach must be false")

    return errors


def wave_order(dependencies: dict, maintenance: dict) -> list[str]:
    """Topo order within maintenance wave start times."""
    assignments = maintenance.get("assignments") or {}
    windows = maintenance.get("windows") or {}

    def wave_start(wl: str) -> str:
        w = assignments.get(wl, "")
        return (windows.get(w) or {}).get("starts", "9999")

    remaining = set(dependencies)
    ordered: list[str] = []
    while remaining:
        ready = [
            wl
            for wl in remaining
            if all(dep in ordered for dep in (dependencies.get(wl) or []))
        ]
        if not ready:
            # cycle or missing dep — break deterministically
            ready = sorted(remaining)
        ready.sort(key=lambda wl: (wave_start(wl), wl))
        pick = ready[0]
        ordered.append(pick)
        remaining.remove(pick)
    return ordered


def seed_snapshots(disks: dict) -> Path:
    snap_root = _var_dir() / "snapshots"
    if snap_root.exists():
        shutil.rmtree(snap_root)
    snap_root.mkdir(parents=True, exist_ok=True)
    for wl, vols in disks.items():
        (snap_root / f"{wl}-root.bin").write_bytes(root_payload(wl))
        for vol in vols:
            path = snap_root / f"{vol['snapshot_id']}.bin"
            path.write_bytes(snapshot_payload(wl, vol["volume_role"], vol["snapshot_id"]))
    return snap_root


def _mount_table_path() -> Path:
    return _var_dir() / "mount-table.json"


def _load_mounts() -> dict:
    p = _mount_table_path()
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _save_mounts(mounts: dict) -> None:
    _var_dir().mkdir(parents=True, exist_ok=True)
    _mount_table_path().write_text(json.dumps(mounts, indent=2), encoding="utf-8")


def materialize_guest(
    workload: str,
    graph: dict,
    disks: dict,
    windows: dict,
    *,
    fail_health: bool = False,
) -> dict:
    """Create a Linux guest directory tree and attach disks exclusively."""
    guests = _var_dir() / "guests"
    guests.mkdir(parents=True, exist_ok=True)
    guest = guests / workload
    if guest.exists():
        shutil.rmtree(guest)
    guest.mkdir(parents=True)
    disks_dir = guest / "disks"
    disks_dir.mkdir()

    mounts = _load_mounts()
    events: list[str] = []

    # restore root
    root_src = _var_dir() / "snapshots" / f"{workload}-root.bin"
    root_dst = disks_dir / "root"
    root_dst.write_bytes(root_src.read_bytes())
    events.append("root_restored")

    attached: list[str] = []
    for vol in disks.get(workload) or []:
        snap_id = vol["snapshot_id"]
        device = vol["device_name"]
        # exclusive mount: refuse if Windows writer still holds it AND we're not releasing
        holder = mounts.get(snap_id)
        if holder and holder not in (f"windows:{workload}", f"linux:{workload}"):
            return {
                "workload": workload,
                "ok": False,
                "reason": f"disk {snap_id} already mounted by {holder}",
                "events": events,
            }
        # release from windows holder for this workload before linux attach
        if holder == f"windows:{workload}":
            del mounts[snap_id]
        src = _var_dir() / "snapshots" / f"{snap_id}.bin"
        dst = disks_dir / device.replace("/", "_")
        dst.write_bytes(src.read_bytes())
        mounts[snap_id] = f"linux:{workload}"
        attached.append(device)
        events.append(f"attached:{device}")

    _save_mounts(mounts)

    health_ok = not fail_health
    checksums = _load("checksums.json")
    verified: dict[str, bool] = {}
    # verify root
    root_key = f"{workload}:root"
    verified[root_key] = sha256_bytes(root_dst.read_bytes()) == checksums.get(root_key)
    for vol in disks.get(workload) or []:
        key = f"{workload}:{vol['device_name']}"
        path = disks_dir / vol["device_name"].replace("/", "_")
        verified[key] = sha256_bytes(path.read_bytes()) == checksums.get(key)
    if not all(verified.values()):
        health_ok = False
        events.append("checksum_mismatch")

    if fail_health:
        events.append("injected_health_failure")
        health_ok = False

    writer = "linux" if health_ok else "windows"
    dns = "linux" if health_ok else "windows"

    if not health_ok:
        # rollback mounts to windows for this workload
        for vol in disks.get(workload) or []:
            snap_id = vol["snapshot_id"]
            if mounts.get(snap_id) == f"linux:{workload}":
                mounts[snap_id] = f"windows:{workload}"
        _save_mounts(mounts)
        # destroy half-booted guest disks claim
        shutil.rmtree(guest, ignore_errors=True)
        events.append("rolled_back_to_windows")

    state = {
        "workload": workload,
        "ok": health_ok,
        "writer": writer,
        "dns": dns,
        "private_ip": graph["instances"][workload]["private_ip"],
        "legacy_instance_id": (windows.get(workload) or {}).get("legacy_instance_id"),
        "dns_name": (windows.get(workload) or {}).get("dns_name"),
        "attached_devices": attached if health_ok else [],
        "checksums_ok": verified,
        "events": events,
        "guest_path": str(guest) if health_ok else None,
    }
    if health_ok:
        (guest / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def init_windows_writers(disks: dict, windows: dict) -> None:
    mounts = {}
    writers = _var_dir() / "windows-writers"
    if writers.exists():
        shutil.rmtree(writers)
    writers.mkdir(parents=True)
    for wl in windows:
        wdir = writers / wl
        wdir.mkdir()
        (wdir / "writer.json").write_text(
            json.dumps({"workload": wl, "writer": "windows", "dns": "windows"}, indent=2),
            encoding="utf-8",
        )
        for vol in disks.get(wl) or []:
            mounts[vol["snapshot_id"]] = f"windows:{wl}"
    _save_mounts(mounts)


def run_rehearsal(
    plan: dict,
    *,
    fail_workload: str | None = None,
) -> dict:
    """Full rehearsal: policy check, seed, wave cutover, journal + report."""
    cmdb = _load("cmdb.json")
    disks = _load("disks.json")
    defaults = _load("defaults.json")
    dependencies = _load("dependencies.json")
    maintenance = _load("maintenance.json")
    windows = _load("windows.json")
    checksums = _load("checksums.json")

    var_dir = _var_dir()
    out_dir = _output_dir()
    var_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    graph = normalize_plan(plan)
    policy_errors = plan_policy_errors(graph, cmdb, disks, defaults)

    journal: list[dict] = []
    status = "READY"
    reason = None

    if policy_errors:
        status = "FAILED"
        reason = "plan_policy"
        report = {
            "status": status,
            "reason": reason,
            "policy_errors": policy_errors,
            "wave_order": [],
            "handoffs": [],
        }
        digest = _report_digest(report)
        report["report_digest"] = digest
        (out_dir / "cutover-journal.json").write_text(
            json.dumps({"entries": journal, "status": status}, indent=2), encoding="utf-8"
        )
        (out_dir / "rehearsal-report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        (var_dir / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        return report

    seed_snapshots(disks)
    init_windows_writers(disks, windows)
    order = wave_order(dependencies, maintenance)
    handoffs: list[dict] = []
    handed = set()

    for wl in order:
        deps = dependencies.get(wl) or []
        if not all(d in handed for d in deps):
            status = "FAILED"
            reason = f"dependency_not_ready:{wl}"
            journal.append({"workload": wl, "event": "blocked_on_deps", "deps": deps})
            break
        guest = materialize_guest(
            wl,
            graph,
            disks,
            windows,
            fail_health=(fail_workload == wl),
        )
        journal.append({"workload": wl, "event": "materialize", "result": guest})
        if not guest["ok"]:
            status = "FAILED"
            reason = f"health_or_attach_failed:{wl}"
            handoffs.append(
                {
                    "workload": wl,
                    "writer": "windows",
                    "dns": "windows",
                    "ok": False,
                }
            )
            break
        handoffs.append(
            {
                "workload": wl,
                "writer": "linux",
                "dns": "linux",
                "ok": True,
                "private_ip": guest["private_ip"],
            }
        )
        handed.add(wl)
        # update windows writer marker
        wpath = var_dir / "windows-writers" / wl / "writer.json"
        wpath.write_text(
            json.dumps({"workload": wl, "writer": "linux", "dns": "linux"}, indent=2),
            encoding="utf-8",
        )

    # dual-mount check
    mounts = _load_mounts()
    holders_by_snap: dict[str, list[str]] = {}
    for snap, holder in mounts.items():
        holders_by_snap.setdefault(snap, []).append(holder)
    dual = {s: h for s, h in holders_by_snap.items() if len(h) > 1}
    if dual:
        status = "FAILED"
        reason = "dual_mount_detected"

    report = {
        "status": status,
        "reason": reason,
        "policy_errors": [],
        "wave_order": order,
        "handoffs": handoffs,
        "checksum_inventory": checksums,
        "mount_table": mounts,
    }
    digest = _report_digest(report)
    report["report_digest"] = digest

    (out_dir / "cutover-journal.json").write_text(
        json.dumps({"entries": journal, "status": status, "wave_order": order}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "rehearsal-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (var_dir / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    return report


def _report_digest(report: dict) -> str:
    stable = {
        "status": report.get("status"),
        "reason": report.get("reason"),
        "wave_order": report.get("wave_order"),
        "handoffs": report.get("handoffs"),
        "policy_errors": report.get("policy_errors"),
    }
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
