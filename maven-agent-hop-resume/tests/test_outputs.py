"""Behavioral checks for the reactor hop/resume interpreter."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path("/app/reactor")
BIN = ROOT / "bin" / "pipe"
JOURNAL = ROOT / "var" / "journal.json"
ARCHIVE = ROOT / "var" / "archive" / "b-1842.log"
FINGERPRINTS = ROOT / "var" / "fingerprints"
PIPELINE = ROOT / "src" / "pipeline.json"
MODULES = ROOT / "src" / "modules.json"
INVENTORY = ROOT / "agents" / "inventory.json"
CRASH = ROOT / "log" / "crash.log"
WEB_SRC = ROOT / "src" / "web" / "src" / "App.java"


def _run(args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [str(BIN), *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


def _journal() -> dict:
    return json.loads(JOURNAL.read_text(encoding="utf-8"))


def _pipeline() -> dict:
    return json.loads(PIPELINE.read_text(encoding="utf-8"))


def _snapshot_runtime() -> dict[str, str | None]:
    work = {}
    for path in (ROOT / "var").rglob("*"):
        if path.is_file():
            work[str(path.relative_to(ROOT))] = path.read_text(encoding="utf-8", errors="replace")
    work["src/web/src/App.java"] = WEB_SRC.read_text(encoding="utf-8")
    work["agents/inventory.json"] = INVENTORY.read_text(encoding="utf-8")
    return work


def _restore_runtime(snap: dict[str, str | None]) -> None:
    for rel, text in snap.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if text is not None:
            path.write_text(text, encoding="utf-8")


def test_f2p_resume_journal_is_success():
    """Resume must finish the crashed run with journal status success."""
    state = _journal()
    assert state["status"] == "success"
    assert state["run_id"] == "b-1842"


def test_f2p_resume_keeps_nightly_run_id():
    """Resume continues b-1842 instead of minting a replacement run id."""
    assert _journal()["run_id"] == _pipeline()["run_id"]


def test_f2p_library_pin_is_exact():
    """Journal library must be the pipeline pin, not the newest directory on disk."""
    pin = _pipeline()["library"]
    lib = _journal()["library"]
    assert lib["name"] == pin["name"]
    assert lib["version"] == pin["version"]
    assert lib["version"] == "1.4.2"


def test_f2p_test_stage_used_maven_agent():
    """The test stage must execute on an agent that carries the maven label."""
    rec = _journal()["stages"]["test"]
    assert rec["status"] == "ok"
    assert "maven" in rec["agent_labels"]
    assert rec["agent_id"] != "docker-07"


def test_f2p_illegal_docker_test_result_discarded():
    """A test result recorded on a docker-only agent is not durable after resume."""
    rec = _journal()["stages"]["test"]
    assert rec["agent_id"] != "docker-07"
    assert rec.get("failed_module") in {None, ""}


def test_f2p_compile_not_rebuilt_on_resume():
    """Durable compile artifacts from maven-03 stay in place across resume."""
    marker = (ROOT / "var" / "work" / "common" / "compile.ok").read_text(encoding="utf-8")
    assert "PRE-CRASH-COMMON" in marker
    rec = _journal()["stages"]["compile"]
    assert rec["agent_id"] == "maven-03"
    assert rec["status"] == "ok"


def test_f2p_completed_stages_cover_pipeline_order():
    """Successful resume lists every pipeline stage in contract order."""
    names = [stage["name"] for stage in _pipeline()["stages"]]
    assert _journal()["completed_stages"] == names
    assert _journal()["resume_from"] is None


def test_f2p_stash_survives_docker_package_hop():
    """The compile stash name remains available for the docker package stage."""
    stash = _journal()["stash"]["reactor-classes"]
    assert set(stash["modules"]) == {"common", "core", "web"}
    assert stash["created_stage"] == "compile"
    assert _journal()["stages"]["package"]["status"] == "ok"
    assert (ROOT / "var" / "work" / "image.ok").is_file()


def test_f2p_archive_redacts_pipeline_secrets():
    """Archived run log must not contain pipeline secret values."""
    text = ARCHIVE.read_text(encoding="utf-8")
    env = _pipeline()["env"]
    assert env["NEXUS_PASSWORD"] not in text
    assert env["BUILD_TOKEN"] not in text
    assert "NEXUS_PASSWORD" in text


def test_f2p_status_cli_matches_journal_file():
    """pipe status prints the on-disk journal object."""
    cp = _run(["status"])
    assert cp.returncode == 0
    printed = json.loads(cp.stdout)
    assert printed["status"] == _journal()["status"]
    assert printed["library"] == _journal()["library"]


def test_f2p_unknown_command_exits_before_journal_write():
    """Unknown pipe commands exit 2 and leave the success journal untouched."""
    before = JOURNAL.read_text(encoding="utf-8")
    cp = _run(["deploy"])
    assert cp.returncode == 2
    assert JOURNAL.read_text(encoding="utf-8") == before


def test_f2p_fingerprint_files_exist_for_modules():
    """Each reactor module has a fingerprint file after a successful resume."""
    for module in json.loads(MODULES.read_text(encoding="utf-8"))["order"]:
        path = FINGERPRINTS / f"{module}.sha256"
        assert path.is_file(), module
        assert len(path.read_text(encoding="utf-8").strip()) == 64


def test_f2p_second_run_skips_unchanged_modules():
    """A later run with incremental library true skips modules whose fingerprints match."""
    snap = _snapshot_runtime()
    try:
        cp = _run(["run"])
        assert cp.returncode == 0, cp.stderr
        rec = _journal()["stages"]["compile"]
        assert rec["status"] == "ok"
        assert set(rec["skipped_modules"]) == {"common", "core", "web"}
        assert rec["modules_ok"] == []
    finally:
        _restore_runtime(snap)


def test_f2p_changed_module_rebuilds_downstream():
    """Editing web invalidates web even when common and core stay skipped."""
    snap = _snapshot_runtime()
    try:
        WEB_SRC.write_text(
            WEB_SRC.read_text(encoding="utf-8") + "\n// hop-touch\n", encoding="utf-8"
        )
        cp = _run(["run"])
        assert cp.returncode == 0, cp.stderr
        rec = _journal()["stages"]["compile"]
        assert "common" in rec["skipped_modules"]
        assert "core" in rec["skipped_modules"]
        assert "web" in rec["modules_ok"]
        assert "web" not in rec["skipped_modules"]
    finally:
        _restore_runtime(snap)


def test_f2p_maven_stage_fails_without_maven_label():
    """A maven stage fails closed when no inventory agent carries the maven label."""
    snap = _snapshot_runtime()
    try:
        INVENTORY.write_text(
            json.dumps(
                {
                    "agents": [
                        {"id": "linux-01", "labels": ["linux", "scm"]},
                        {"id": "docker-07", "labels": ["linux", "docker"]},
                    ]
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        cp = _run(["run"])
        assert cp.returncode != 0
        state = _journal()
        assert state["status"] == "failed"
        compile_rec = state["stages"]["compile"]
        assert compile_rec["status"] == "failed"
        assert "maven" not in compile_rec.get("agent_labels", [])
    finally:
        _restore_runtime(snap)


def test_f2p_package_fails_without_named_stash():
    """Docker package fails closed when the required stash name is absent."""
    snap = _snapshot_runtime()
    state = _journal()
    state["stash"] = {}
    for name in ("package", "test"):
        state["stages"].pop(name, None)
    state["completed_stages"] = [
        n for n in state["completed_stages"] if n not in {"package", "test"}
    ]
    state["status"] = "crashed"
    JOURNAL.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    try:
        cp = _run(["resume"])
        assert cp.returncode != 0
        assert _journal()["status"] == "failed"
        failed = [
            name
            for name, rec in _journal()["stages"].items()
            if rec.get("status") == "failed"
        ]
        assert failed
    finally:
        _restore_runtime(snap)


def test_f2p_crash_log_names_failed_hop():
    """Crash evidence still identifies the illegal test hop that resume had to repair."""
    text = CRASH.read_text(encoding="utf-8")
    assert "stage=test" in text
    assert "docker-07" in text
    assert "b-1842" in text


def test_p2p_pipeline_library_pin_untouched():
    """Repairs must not rewrite the public pipeline pin to match a wrong load."""
    pin = _pipeline()["library"]
    assert pin == {"name": "platform-lib", "version": "1.4.2"}


def test_p2p_module_graph_preserved():
    """The baked reactor module graph stays the public common/core/web tree."""
    modules = json.loads(MODULES.read_text(encoding="utf-8"))
    assert modules["order"] == ["common", "core", "web"]
    assert modules["graph"]["web"] == ["core"]


def test_p2p_crash_log_file_retained():
    """Incident crash log remains in place for operators after resume."""
    assert CRASH.is_file()
    assert CRASH.stat().st_size > 80


def test_p2p_pipe_binary_still_dispatches():
    """Public pipe entrypoint remains executable for run, resume, and status."""
    assert BIN.is_file()
    assert os.access(BIN, os.X_OK)
    assert shutil.which is not None
    cp = _run(["status"])
    assert cp.returncode == 0
