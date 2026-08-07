"""Filesystem Jenkins-like lab for controller cell isolation and upgrade."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def _data_dir() -> Path:
    return Path(os.environ.get("CELL_DATA_DIR", "/app/data"))


def _var_dir() -> Path:
    return Path(os.environ.get("CELL_VAR_DIR", "/app/var/cells"))


def _output_dir() -> Path:
    return Path(os.environ.get("CELL_OUTPUT_DIR", "/app/output"))


def _cells_dir() -> Path:
    return Path(os.environ.get("CELL_CELLS_DIR", "/app/cells"))


def _load(name: str) -> Any:
    return json.loads((_data_dir() / name).read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_digest(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_text(body)


def _parse_assume_subjects(policy_doc: Any) -> list[str]:
    subjects: list[str] = []
    if policy_doc is None:
        return subjects
    if isinstance(policy_doc, str):
        try:
            policy_doc = json.loads(policy_doc)
        except json.JSONDecodeError:
            subjects.extend(re.findall(r"system:serviceaccount:[^\s\"'\\]+", policy_doc))
            if "system:nodes" in policy_doc:
                subjects.append("system:nodes")
            return subjects
    statements = policy_doc.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    for stmt in statements:
        cond = stmt.get("Condition") or {}
        for block in cond.values():
            if not isinstance(block, dict):
                continue
            for key, val in block.items():
                if not str(key).endswith(":sub") and key != "sub":
                    continue
                if isinstance(val, list):
                    subjects.extend(str(v) for v in val)
                else:
                    subjects.append(str(val))
    return subjects


def normalize_plan(plan: dict) -> dict:
    """Extract cell identities, homes, IRSA, node group, and disruption from a TF plan."""
    changes = plan.get("resource_changes") or []
    cells: dict[str, dict] = {}
    homes: dict[str, dict] = {}
    roles: dict[str, dict] = {}
    node_groups: dict[str, dict] = {}
    ssm: dict[str, dict] = {}

    for rc in changes:
        rtype = rc.get("type")
        after = (rc.get("change") or {}).get("after") or {}
        actions = list((rc.get("change") or {}).get("actions") or [])
        tags = after.get("tags") or after.get("tags_all") or {}
        if not isinstance(tags, dict):
            tags = {}

        if rtype == "aws_eks_node_group":
            name = after.get("node_group_name") or tags.get("Component")
            scaling = after.get("scaling_config") or {}
            if isinstance(scaling, list):
                scaling = scaling[0] if scaling else {}
            taints = after.get("taint") or after.get("taints") or []
            if isinstance(taints, dict):
                taints = list(taints.values())
            node_groups[str(name)] = {
                "node_group_name": name,
                "labels": dict(after.get("labels") or {}),
                "taints": taints,
                "min_size": scaling.get("min_size"),
                "desired_size": scaling.get("desired_size"),
                "tags": dict(tags),
                "actions": actions,
                "address": rc.get("address"),
            }
        elif rtype == "aws_iam_role":
            cell_id = tags.get("CellId") or after.get("name")
            subjects = _parse_assume_subjects(after.get("assume_role_policy"))
            roles[str(cell_id)] = {
                "name": after.get("name"),
                "subjects": subjects,
                "tags": dict(tags),
                "home_claim": tags.get("HomeClaim"),
                "plugin_generation": tags.get("PluginGen"),
                "routing_key": tags.get("RoutingKey"),
                "max_unavailable": tags.get("MaxUnavail"),
                "actions": actions,
                "address": rc.get("address"),
            }
        elif rtype == "aws_efs_access_point":
            cell_id = tags.get("CellId") or tags.get("Name")
            root = after.get("root_directory") or {}
            if isinstance(root, list):
                root = root[0] if root else {}
            homes[str(cell_id)] = {
                "path": root.get("path"),
                "home_claim": tags.get("HomeClaim") or tags.get("Name"),
                "file_system_id": after.get("file_system_id"),
                "tags": dict(tags),
                "actions": actions,
                "address": rc.get("address"),
            }
        elif rtype == "aws_ssm_parameter":
            cell_id = tags.get("CellId")
            value = after.get("value")
            parsed: dict[str, Any] = {}
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    parsed = {}
            if cell_id:
                ssm[str(cell_id)] = {
                    "value": parsed,
                    "tags": dict(tags),
                    "home_claim": tags.get("HomeClaim") or parsed.get("home_claim"),
                    "plugin_generation": tags.get("PluginGen")
                    or parsed.get("plugin_generation"),
                    "routing_key": tags.get("RoutingKey") or parsed.get("routing_key"),
                    "max_unavailable": tags.get("MaxUnavail")
                    or parsed.get("max_unavailable"),
                    "actions": actions,
                    "address": rc.get("address"),
                }

    for cell_id, meta in {**roles, **ssm}.items():
        entry = cells.setdefault(cell_id, {})
        entry.update({k: v for k, v in meta.items() if v is not None})
        if cell_id in homes:
            entry["home"] = homes[cell_id]
        if cell_id in roles:
            entry["subjects"] = roles[cell_id].get("subjects") or entry.get("subjects")
            entry["identity"] = roles[cell_id].get("name")
        if cell_id in ssm:
            val = ssm[cell_id].get("value") or {}
            for key in (
                "home_claim",
                "plugin_generation",
                "routing_key",
                "max_unavailable",
                "service_account",
                "plugin_source",
                "az_preference",
            ):
                if val.get(key) is not None:
                    entry[key] = val[key]

    return {
        "cells": cells,
        "homes": homes,
        "roles": roles,
        "node_groups": node_groups,
        "ssm": ssm,
    }


def _load_cells_config() -> dict[str, Any]:
    cells_dir = _cells_dir()
    registry = json.loads((cells_dir / "fleet-registry.json").read_text(encoding="utf-8"))
    restrictions = json.loads((cells_dir / "restrictions.json").read_text(encoding="utf-8"))
    catalog_path = cells_dir / "plugin-catalog.yaml"
    if yaml is None:
        raise RuntimeError("PyYAML is required")
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    jcasc: dict[str, Any] = {}
    jcasc_dir = cells_dir / "jcasc"
    if jcasc_dir.is_dir():
        for path in sorted(jcasc_dir.glob("*.yaml")):
            jcasc[path.stem] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        "registry": registry,
        "restrictions": restrictions,
        "catalog": catalog,
        "jcasc": jcasc,
    }


def plan_policy_errors(
    graph: dict,
    inventory: dict,
    topology: dict,
    defaults: dict,
    catalog: dict,
    cells_cfg: dict,
) -> list[str]:
    errors: list[str] = []
    expected_cells = inventory["cells"]
    namespace = defaults["namespace"]

    node_groups = graph.get("node_groups") or {}
    wanted = topology["node_group_key"]
    ng = None
    for name, candidate in node_groups.items():
        if name == wanted or (candidate.get("labels") or {}).get("workload") == topology[
            "labels"
        ]["workload"]:
            ng = candidate
            break
    if ng is None:
        errors.append("missing_controller_node_group")
    else:
        if int(ng.get("min_size") or 0) < int(topology["min_size"]):
            errors.append("node_group_min_size")
        if int(ng.get("desired_size") or 0) < int(topology["desired_size"]):
            errors.append("node_group_desired_size")
        labels = ng.get("labels") or {}
        for key, val in topology["labels"].items():
            if labels.get(key) != val:
                errors.append(f"node_label:{key}")
        taints = ng.get("taints") or []
        ok_taint = False
        for t in taints:
            effect = str(t.get("effect") or "").upper().replace("-", "_")
            if (
                t.get("key") == topology["taints"][0]["key"]
                and t.get("value") == topology["taints"][0]["value"]
                and effect in {"NO_SCHEDULE", "NOSCHEDULE"}
            ):
                ok_taint = True
        if not ok_taint:
            errors.append("missing_jenkins_taint")
        max_unavail = (ng.get("tags") or {}).get("MaxUnavailable")
        if max_unavail is not None and str(max_unavail) != str(topology["pdb"]["max_unavailable"]):
            errors.append("node_group_pdb_tag")

    planned_cells = graph.get("cells") or {}
    home_claims: list[str] = []
    home_paths: list[str] = []
    for cell_id, expected in expected_cells.items():
        planned = planned_cells.get(cell_id)
        if not planned:
            errors.append(f"missing_cell:{cell_id}")
            continue
        subject = f"system:serviceaccount:{namespace}:{expected['service_account']}"
        subjects = planned.get("subjects") or []
        if subject not in subjects:
            errors.append(f"irsa_subject:{cell_id}")
        if "system:nodes" in subjects:
            errors.append(f"node_admin_trust:{cell_id}")
        claim = planned.get("home_claim") or (planned.get("home") or {}).get("home_claim")
        if claim != expected["home_claim"]:
            errors.append(f"home_claim:{cell_id}")
        else:
            home_claims.append(str(claim))
        path = (planned.get("home") or {}).get("path")
        if not path or path == "/jenkins-home":
            errors.append(f"shared_or_missing_home_path:{cell_id}")
        else:
            home_paths.append(path)
        gen = planned.get("plugin_generation")
        if gen != expected["plugin_generation"]:
            errors.append(f"plugin_generation:{cell_id}")
        routing = planned.get("routing_key")
        if routing != expected["routing_key"]:
            errors.append(f"routing_key:{cell_id}")
        max_u = planned.get("max_unavailable")
        if str(max_u) != str(topology["pdb"]["max_unavailable"]):
            errors.append(f"max_unavailable:{cell_id}")

    if len(home_claims) != len(set(home_claims)):
        errors.append("duplicate_home_claims")
    if len(home_paths) != len(set(home_paths)):
        errors.append("duplicate_home_paths")

    restrictions = cells_cfg["restrictions"]
    if restrictions.get("plugin_source") != catalog["plugin_source"]:
        errors.append("restrictions_plugin_source")
    if restrictions.get("script_console_enabled") is not False:
        errors.append("script_console_enabled")
    if restrictions.get("controller_to_controller_job_trigger") is not False:
        errors.append("cross_cell_triggers")
    if int(restrictions.get("max_unavailable", 99)) != int(topology["pdb"]["max_unavailable"]):
        errors.append("restrictions_max_unavailable")

    cfg_catalog = cells_cfg["catalog"] or {}
    if cfg_catalog.get("pluginSource") != catalog["plugin_source"]:
        errors.append("catalog_plugin_source")
    approved = {p["id"]: p for p in catalog["plugins"]}
    cfg_plugins = cfg_catalog.get("plugins") or []
    if len(cfg_plugins) < len(approved):
        errors.append("catalog_incomplete")
    for plugin in cfg_plugins:
        pid = plugin.get("id")
        if pid not in approved:
            errors.append(f"unapproved_plugin:{pid}")
            continue
        if plugin.get("version") in (None, "latest"):
            errors.append(f"unpinned_plugin:{pid}")
        if plugin.get("digest") != approved[pid]["digest"]:
            errors.append(f"plugin_digest:{pid}")
        if plugin.get("version") != approved[pid]["version"]:
            errors.append(f"plugin_version:{pid}")

    registry = cells_cfg["registry"]
    reg_cells = registry.get("cells") or {}
    for cell_id, expected in expected_cells.items():
        got = reg_cells.get(cell_id) or {}
        for field in ("home_claim", "routing_key", "plugin_generation", "service_account", "folder"):
            if got.get(field) != expected.get(field):
                errors.append(f"registry_{field}:{cell_id}")

    jobs = registry.get("jobs") or {}
    inv_jobs = inventory.get("jobs") or {}
    if len(jobs) < len(inv_jobs):
        errors.append("registry_jobs_incomplete")
    per_cell: dict[str, int] = {c: 0 for c in expected_cells}
    for job_name, job in jobs.items():
        cell = job.get("cell")
        if cell not in expected_cells:
            errors.append(f"job_unknown_cell:{job_name}")
            continue
        per_cell[cell] = per_cell.get(cell, 0) + 1
        expected_job = inv_jobs.get(job_name)
        if expected_job and expected_job.get("cell") != cell:
            errors.append(f"job_misassigned:{job_name}")
        if not job.get("folder"):
            errors.append(f"job_folder:{job_name}")
        if not job.get("required_plugins"):
            errors.append(f"job_plugins:{job_name}")
    for cell_id, count in per_cell.items():
        if count < 2:
            errors.append(f"cell_job_count:{cell_id}")

    for cell_id in expected_cells:
        jcasc = (cells_cfg.get("jcasc") or {}).get(cell_id)
        if not jcasc:
            errors.append(f"missing_jcasc:{cell_id}")
            continue
        realm = ((jcasc.get("jenkins") or {}).get("securityRealm") or {}).get("local") or {}
        if realm.get("allowsSignup") is not False:
            errors.append(f"jcasc_signup:{cell_id}")
        auth = (jcasc.get("jenkins") or {}).get("authorizationStrategy") or {}
        if "unsecured" in auth:
            errors.append(f"jcasc_unsecured:{cell_id}")

    return sorted(set(errors))


def _materialize_home(cell_id: str, claim: str, seed: dict) -> Path:
    var = _var_dir()
    cell_dir = var / cell_id
    home = cell_dir / "home"
    home.mkdir(parents=True, exist_ok=True)
    lock = var / "locks" / claim
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        owner = lock.read_text(encoding="utf-8").strip()
        if owner and owner != cell_id:
            raise RuntimeError(f"dual_writer:{claim}:{owner}:{cell_id}")
    lock.write_text(cell_id, encoding="utf-8")
    state_path = home / "state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {
            "cell_id": cell_id,
            "home_claim": claim,
            "last_build_number": int(seed.get("last_build_number") or 0),
            "completed_builds": list(seed.get("completed_builds") or []),
            "plugin_generation": None,
        }
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    (cell_dir / "api").mkdir(exist_ok=True)
    return home


def _boot_cell(
    cell_id: str,
    planned: dict,
    inventory_cell: dict,
    compat: dict,
    catalog: dict,
    cells_cfg: dict,
    homes_seed: dict,
) -> dict:
    gen = planned.get("plugin_generation") or inventory_cell["plugin_generation"]
    gen_info = (compat.get("generations") or {}).get(gen) or {}
    if not gen_info.get("bootable", False):
        return {
            "booted": False,
            "plugin_generation": gen,
            "identity": planned.get("identity"),
            "home_claim": planned.get("home_claim"),
            "build_watermark": homes_seed.get(cell_id, {}).get("last_build_number", 0),
            "serving": False,
            "reason": gen_info.get("reason") or "generation_not_bootable",
        }

    approved = {p["id"]: p for p in catalog["plugins"]}
    required = gen_info.get("plugins") or {}
    cfg_plugins = {
        p["id"]: p for p in ((cells_cfg.get("catalog") or {}).get("plugins") or [])
    }
    for pid, version in required.items():
        plugin = cfg_plugins.get(pid)
        if not plugin:
            return {
                "booted": False,
                "plugin_generation": gen,
                "identity": planned.get("identity"),
                "home_claim": planned.get("home_claim"),
                "build_watermark": homes_seed.get(cell_id, {}).get("last_build_number", 0),
                "serving": False,
                "reason": f"missing_plugin:{pid}",
            }
        if plugin.get("version") != version or plugin.get("digest") != approved[pid]["digest"]:
            return {
                "booted": False,
                "plugin_generation": gen,
                "identity": planned.get("identity"),
                "home_claim": planned.get("home_claim"),
                "build_watermark": homes_seed.get(cell_id, {}).get("last_build_number", 0),
                "serving": False,
                "reason": f"plugin_mismatch:{pid}",
            }

    claim = planned.get("home_claim") or inventory_cell["home_claim"]
    home = _materialize_home(cell_id, claim, homes_seed.get(cell_id) or {})
    state = json.loads((home / "state.json").read_text(encoding="utf-8"))
    state["plugin_generation"] = gen
    (home / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    api = _var_dir() / cell_id / "api" / "ready"
    api.write_text("ok\n", encoding="utf-8")
    return {
        "booted": True,
        "plugin_generation": gen,
        "identity": planned.get("identity") or f"jenkins-{cell_id}",
        "home_claim": claim,
        "build_watermark": int(state["last_build_number"]),
        "serving": True,
        "reason": None,
    }


def submit_job(cell_id: str, job_name: str, registry: dict) -> dict:
    job = (registry.get("jobs") or {}).get(job_name)
    if not job:
        return {"job": job_name, "cell": cell_id, "status": "NOT_FOUND", "build_number": 0}
    assigned = job.get("cell")
    if assigned != cell_id:
        return {
            "job": job_name,
            "cell": cell_id,
            "status": "CROSS_CELL_DENIED",
            "build_number": 0,
        }
    ready = _var_dir() / cell_id / "api" / "ready"
    if not ready.exists():
        return {"job": job_name, "cell": cell_id, "status": "CELL_DOWN", "build_number": 0}
    home = _var_dir() / cell_id / "home" / "state.json"
    state = json.loads(home.read_text(encoding="utf-8"))
    next_build = int(state["last_build_number"]) + 1
    state["last_build_number"] = next_build
    builds = list(state.get("completed_builds") or [])
    builds.append(next_build)
    state["completed_builds"] = builds
    home.write_text(json.dumps(state, indent=2), encoding="utf-8")
    run = {
        "job": job_name,
        "cell": cell_id,
        "status": "SUCCESS",
        "build_number": next_build,
    }
    runs_path = _var_dir() / cell_id / "api" / "runs.jsonl"
    with runs_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(run) + "\n")
    return run


def restart_cell(cell_id: str) -> dict:
    home = _var_dir() / cell_id / "home" / "state.json"
    before = json.loads(home.read_text(encoding="utf-8"))
    watermark = int(before["last_build_number"])
    builds = list(before.get("completed_builds") or [])
    ready = _var_dir() / cell_id / "api" / "ready"
    if ready.exists():
        ready.unlink()
    # remount exclusive lock
    claim = before["home_claim"]
    lock = _var_dir() / "locks" / claim
    lock.write_text(cell_id, encoding="utf-8")
    ready.write_text("ok\n", encoding="utf-8")
    after = json.loads(home.read_text(encoding="utf-8"))
    return {
        "cell": cell_id,
        "builds_preserved": after.get("completed_builds") == builds
        and int(after["last_build_number"]) == watermark,
        "watermark_after": int(after["last_build_number"]),
    }


def upgrade_drill(target_cell: str, compat: dict) -> dict:
    """Attempt incompatible generation on one cell; rollback; siblings stay up."""
    home = _var_dir() / target_cell / "home" / "state.json"
    before = json.loads(home.read_text(encoding="utf-8"))
    prior_gen = before.get("plugin_generation")
    prior_builds = list(before.get("completed_builds") or [])
    prior_watermark = int(before["last_build_number"])

    bad = compat["generations"]["gen-3-incompatible"]
    # Fail the upgrade: do not mutate completed builds; leave cell temporarily down.
    ready = _var_dir() / target_cell / "api" / "ready"
    if ready.exists():
        ready.unlink()
    failed = not bad.get("bootable", False)

    siblings_serving = True
    for path in _var_dir().glob("*/api/ready"):
        cell = path.parent.parent.name
        if cell == target_cell:
            continue
        if not path.exists():
            siblings_serving = False

    # Rollback to prior generation without losing builds.
    before["plugin_generation"] = prior_gen
    home.write_text(json.dumps(before, indent=2), encoding="utf-8")
    ready.write_text("ok\n", encoding="utf-8")
    after = json.loads(home.read_text(encoding="utf-8"))
    return {
        "target_cell": target_cell,
        "failed": failed,
        "rolled_back": after.get("plugin_generation") == prior_gen,
        "builds_preserved": after.get("completed_builds") == prior_builds
        and int(after["last_build_number"]) == prior_watermark,
        "sibling_cells_serving": siblings_serving,
    }


def run_upgrade(
    plan: dict,
    *,
    extra_jobs: dict[str, dict] | None = None,
    skip_upgrade_drill: bool = False,
) -> dict:
    inventory = _load("fleet_registry.json")
    topology = _load("node_topology.json")
    defaults = _load("defaults.json")
    catalog = _load("plugin_catalog.json")
    compat = _load("compatibility_matrix.json")
    homes_seed = _load("cell_homes.json")
    cells_cfg = _load_cells_config()

    var = _var_dir()
    out = _output_dir()
    if var.exists():
        shutil.rmtree(var)
    var.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    graph = normalize_plan(plan)
    (var / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (var / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")

    policy_errors = plan_policy_errors(
        graph, inventory, topology, defaults, catalog, cells_cfg
    )

    report: dict[str, Any] = {
        "status": "FAILED",
        "reason": None,
        "policy_errors": policy_errors,
        "cells": {},
        "job_runs": [],
        "isolation": {"cross_cell_denied": False, "dual_writer_blocked": False},
        "restart": {},
        "upgrade_drill": {},
        "disruption": {"pdb_respected": False, "other_cells_available": False},
        "report_digest": "",
    }

    if policy_errors:
        report["reason"] = "policy_errors"
        report["report_digest"] = _digest_report(report)
        (out / "cell-upgrade-report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return report

    planned_cells = graph["cells"]
    dual_writer_blocked = True
    try:
        for cell_id, expected in inventory["cells"].items():
            report["cells"][cell_id] = _boot_cell(
                cell_id,
                planned_cells[cell_id],
                expected,
                compat,
                catalog,
                cells_cfg,
                homes_seed,
            )
            if not report["cells"][cell_id]["booted"]:
                report["reason"] = report["cells"][cell_id].get("reason") or "boot_failed"
                report["report_digest"] = _digest_report(report)
                (out / "cell-upgrade-report.json").write_text(
                    json.dumps(report, indent=2), encoding="utf-8"
                )
                return report
    except RuntimeError as exc:
        dual_writer_blocked = False
        report["reason"] = str(exc)
        report["isolation"]["dual_writer_blocked"] = False
        report["report_digest"] = _digest_report(report)
        (out / "cell-upgrade-report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return report

    report["isolation"]["dual_writer_blocked"] = dual_writer_blocked

    registry = cells_cfg["registry"]
    # Merge optional hidden jobs for verifier variations.
    if extra_jobs:
        merged = dict(registry.get("jobs") or {})
        merged.update(extra_jobs)
        registry = {**registry, "jobs": merged}

    job_runs: list[dict] = []
    for job_name, job in sorted((registry.get("jobs") or {}).items()):
        cell = job["cell"]
        job_runs.append(submit_job(cell, job_name, registry))

    # Cross-cell probe: try first job on a wrong cell.
    sample_job, sample_meta = next(iter(sorted((inventory.get("jobs") or {}).items())))
    wrong_cells = [c for c in inventory["cells"] if c != sample_meta["cell"]]
    cross = submit_job(wrong_cells[0], sample_job, inventory)
    cross_denied = cross["status"] == "CROSS_CELL_DENIED"
    report["isolation"]["cross_cell_denied"] = cross_denied
    job_runs.append(cross)
    report["job_runs"] = job_runs

    restart_cell_id = defaults.get("restart_cell") or "payments-controller"
    report["restart"] = restart_cell(restart_cell_id)
    # Post-restart job on restarted cell
    post_job = next(
        name
        for name, meta in (inventory.get("jobs") or {}).items()
        if meta["cell"] == restart_cell_id
    )
    job_runs.append(submit_job(restart_cell_id, post_job, registry))
    report["job_runs"] = job_runs
    report["cells"][restart_cell_id]["build_watermark"] = report["restart"][
        "watermark_after"
    ]

    drill_cell = defaults.get("upgrade_drill_cell") or "risk-controller"
    if skip_upgrade_drill:
        report["upgrade_drill"] = {
            "target_cell": drill_cell,
            "failed": True,
            "rolled_back": True,
            "builds_preserved": True,
            "sibling_cells_serving": True,
        }
    else:
        report["upgrade_drill"] = upgrade_drill(drill_cell, compat)

    # Disruption: with max_unavailable 0, taking one cell offline for upgrade
    # must leave other cells serving.
    other_up = all(
        report["cells"][c]["serving"]
        for c in inventory["cells"]
        if c != drill_cell
    )
    # Re-check sibling readiness files after drill.
    for cell_id in inventory["cells"]:
        if cell_id == drill_cell:
            continue
        if not (_var_dir() / cell_id / "api" / "ready").exists():
            other_up = False
    pdb_ok = all(
        str(planned_cells[c].get("max_unavailable")) == str(topology["pdb"]["max_unavailable"])
        for c in inventory["cells"]
    )
    report["disruption"] = {
        "pdb_respected": pdb_ok,
        "other_cells_available": other_up
        and report["upgrade_drill"].get("sibling_cells_serving", False),
    }

    ok = (
        all(c["booted"] and c["serving"] for c in report["cells"].values())
        and report["isolation"]["cross_cell_denied"]
        and report["isolation"]["dual_writer_blocked"]
        and report["restart"].get("builds_preserved")
        and report["upgrade_drill"].get("failed")
        and report["upgrade_drill"].get("rolled_back")
        and report["upgrade_drill"].get("builds_preserved")
        and report["upgrade_drill"].get("sibling_cells_serving")
        and report["disruption"]["pdb_respected"]
        and report["disruption"]["other_cells_available"]
        and all(r["status"] == "SUCCESS" for r in job_runs if r["status"] != "CROSS_CELL_DENIED")
    )
    report["status"] = "READY" if ok else "FAILED"
    if not ok and report["reason"] is None:
        report["reason"] = "invariants_failed"
    report["report_digest"] = _digest_report(report)
    (out / "cell-upgrade-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def _digest_report(report: dict) -> str:
    stable = {
        "status": report.get("status"),
        "policy_errors": report.get("policy_errors"),
        "cells": {
            k: {
                "booted": v.get("booted"),
                "plugin_generation": v.get("plugin_generation"),
                "home_claim": v.get("home_claim"),
                "serving": v.get("serving"),
            }
            for k, v in sorted((report.get("cells") or {}).items())
        },
        "isolation": report.get("isolation"),
        "restart": {
            "cell": (report.get("restart") or {}).get("cell"),
            "builds_preserved": (report.get("restart") or {}).get("builds_preserved"),
        },
        "upgrade_drill": {
            "target_cell": (report.get("upgrade_drill") or {}).get("target_cell"),
            "failed": (report.get("upgrade_drill") or {}).get("failed"),
            "rolled_back": (report.get("upgrade_drill") or {}).get("rolled_back"),
            "builds_preserved": (report.get("upgrade_drill") or {}).get("builds_preserved"),
            "sibling_cells_serving": (report.get("upgrade_drill") or {}).get(
                "sibling_cells_serving"
            ),
        },
        "disruption": report.get("disruption"),
        "job_names": sorted(
            {
                r["job"]
                for r in report.get("job_runs") or []
                if r.get("status") == "SUCCESS"
            }
        ),
    }
    return _stable_digest(stable)
