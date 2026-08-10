from __future__ import annotations

from pathlib import Path

from engine import archive, fingerprint, journal as journal_mod, library, stash
from engine.agents import agent_is_legal, select_agent
from engine.paths import KIND_LABEL, WORK
from engine.pipeline import load_modules, load_pipeline, module_order


def _artifact(module: str, goal: str) -> Path:
    path = WORK / module / f"{goal}.ok"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _run_module(module: str, goal: str) -> None:
    marker = _artifact(module, goal)
    digest = fingerprint.module_fingerprint(module)
    marker.write_text(f"{goal}:{digest}\n", encoding="utf-8")
    fingerprint.write_fingerprint(module, digest)


def execute(pipeline: dict, *, resume: bool) -> dict:
    modules_cfg = load_modules()
    order = module_order(modules_cfg)
    graph = modules_cfg["graph"]
    lib = library.resolve(pipeline["library"])
    env = pipeline.get("env", {})
    log_lines: list[str] = []

    if resume:
        state = journal_mod.load_journal()
        state["run_id"] = pipeline.get("run_id", state.get("run_id", "b-1842"))
        # Starter resume: throw away durability and rebuild every stage.
        state["stages"] = {}
        state["completed_stages"] = []
        state["stash"] = {}
        start_index = 0
    else:
        state = {
            "run_id": pipeline.get("run_id", "run-new"),
            "status": "running",
            "library": {"name": lib["name"], "version": lib["version"]},
            "completed_stages": [],
            "resume_from": None,
            "stages": {},
            "stash": {},
        }
        start_index = 0

    state["library"] = {"name": lib["name"], "version": lib["version"]}
    state["status"] = "running"
    journal_mod.save_journal(state)

    stages = pipeline["stages"]
    for index, stage in enumerate(stages):
        name = stage["name"]
        kind = stage["kind"]
        if index < start_index:
            continue

        agent = select_agent(kind)
        rec = {
            "status": "running",
            "agent_id": agent["id"],
            "agent_labels": list(agent["labels"]),
            "modules_ok": [],
            "skipped_modules": [],
            "failed_module": None,
        }
        state["stages"][name] = rec
        state["resume_from"] = name
        journal_mod.save_journal(state)

        if not agent_is_legal(agent, kind):
            rec["status"] = "failed"
            rec["failed_module"] = stage.get("goal") or kind
            state["status"] = "failed"
            log_lines.append(f"{name} refused: agent {agent['id']} missing {KIND_LABEL[kind]}")
            archive.write_archive(state["run_id"], env, lib, log_lines)
            journal_mod.save_journal(state)
            return state

        unstash_name = stage.get("unstash")
        if unstash_name and not stash.has_stash(state, unstash_name):
            rec["status"] = "failed"
            state["status"] = "failed"
            log_lines.append(f"{name} missing stash {unstash_name}")
            archive.write_archive(state["run_id"], env, lib, log_lines)
            journal_mod.save_journal(state)
            return state

        skipped: list[str] = []
        ok: list[str] = []
        if kind == "scm":
            log_lines.append(f"{name} checkout on {agent['id']}")
            rec["status"] = "ok"
        elif kind == "maven":
            durable_prior = set()
            goal = stage.get("goal", "compile")
            for module in order:
                missing_dep = [dep for dep in graph[module] if dep not in ok and dep not in skipped]
                if missing_dep:
                    rec["status"] = "failed"
                    rec["failed_module"] = module
                    state["status"] = "failed"
                    log_lines.append(f"{name} blocked on {module} deps {missing_dep}")
                    archive.write_archive(state["run_id"], env, lib, log_lines)
                    journal_mod.save_journal(state)
                    return state
                # Starter: never skip; rebuild every module every hop.
                _run_module(module, goal)
                ok.append(module)
                log_lines.append(f"{name} rebuilt {module} on {agent['id']}")
            rec["modules_ok"] = ok
            rec["skipped_modules"] = skipped
            rec["status"] = "ok"
            if stage.get("stash"):
                stash.put_stash(state, stage["stash"], ok + skipped, name)
        elif kind == "docker":
            image = WORK / "image.ok"
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_text("ok\n", encoding="utf-8")
            rec["status"] = "ok"
            rec["modules_ok"] = list(order)
            log_lines.append(f"{name} image on {agent['id']}")
        else:
            rec["status"] = "failed"
            state["status"] = "failed"
            journal_mod.save_journal(state)
            return state

        if name not in state["completed_stages"]:
            state["completed_stages"].append(name)
        journal_mod.save_journal(state)

    state["status"] = "success"
    state["resume_from"] = None
    archive.write_archive(state["run_id"], env, lib, log_lines)
    journal_mod.save_journal(state)
    return state


def run_new(pipeline_path: Path | None = None) -> dict:
    return execute(load_pipeline(pipeline_path), resume=False)


def resume() -> dict:
    pipeline = load_pipeline()
    return execute(pipeline, resume=True)
