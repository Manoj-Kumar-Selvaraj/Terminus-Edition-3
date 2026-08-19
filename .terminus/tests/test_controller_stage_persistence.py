from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/terminus-controller-stage.yml"


def test_hosted_controller_commits_only_durable_execution_evidence() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'git add -- ".terminus/executions/$TASK"' in workflow
    assert (
        'git add -- ".terminus/executions/$TASK" ".terminus/workflows/$TASK"'
        not in workflow
    )

    # Materialized workflow state remains an allowed in-run mutation so the
    # recorder/resolver can replay it, but it is not durable acceptance evidence.
    assert '^\\.terminus/(executions|workflows)/$TASK(/|$)' in workflow


def test_materialized_workflow_state_is_git_ignored_and_rebuildable() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".terminus/workflows/" in gitignore

    ignored = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "check-ignore",
            ".terminus/workflows/controller-stage-persistence-test/state.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0
