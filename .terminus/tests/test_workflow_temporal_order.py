from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / ".terminus" / "tests"
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.state import WorkflowStateResolver  # noqa: E402
from test_workflow_state import (  # noqa: E402
    _append_through_freeze_predecessor,
    _record,
    _temp_control_repo,
)


def test_same_commit_upstream_rerun_invalidates_older_downstream_records(
    tmp_path: Path,
) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ledger = _append_through_freeze_predecessor(
        root,
        resolver,
        "task-temporal",
        commit,
    )

    # Re-run an early stage on the same exact task/control snapshot. Even though
    # downstream records still match those commits, they predate the new upstream
    # execution and therefore cannot remain current.
    ledger.append(
        _record(
            resolver,
            "WORK_PACKAGE_RESEARCH",
            "task-temporal",
            commit,
            attempt=2,
        )
    )

    state = resolver.resolve(
        task_id="task-temporal",
        task_commit=commit,
        control_plane_commit=commit,
    )
    work = next(
        node for node in state["nodes"] if node["node_id"] == "WORK_PACKAGE_RESEARCH"
    )
    architecture = next(
        node for node in state["nodes"] if node["node_id"] == "SYSTEM_ARCHITECTURE"
    )

    assert work["status"] == "CURRENT"
    assert architecture["status"] == "STALE"
    assert "predates the latest current predecessor" in architecture["reason"]
    assert state["next"]["action"] == "INVOKE_STAGE"
    assert state["next"]["stage_id"] == "SYSTEM_ARCHITECTURE"
