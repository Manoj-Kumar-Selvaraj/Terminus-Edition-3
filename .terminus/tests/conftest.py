from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.record import ExecutionRecordBuilder  # noqa: E402


@pytest.fixture(autouse=True)
def _complete_external_gate_temp_snapshot(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
):
    """Complete the isolated Pass-B controller fixture without changing shared tests."""
    if not request.module.__name__.endswith("test_external_gate_controller"):
        yield
        return

    original_repo = request.module._temp_control_repo
    original_record = request.module._record
    valid_outputs = original_record.__globals__["_valid_outputs"]

    def wrapped_repo(tmp_path: Path):
        root, _commit = original_repo(tmp_path)
        shutil.copy2(
            ROOT / ".terminus" / "AGENT_SYSTEM.md",
            root / ".terminus" / "AGENT_SYSTEM.md",
        )
        subprocess.run(
            ["git", "-C", str(root), "add", ".terminus/AGENT_SYSTEM.md"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "commit", "--amend", "--no-edit"],
            check=True,
            capture_output=True,
        )
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return root, commit

    def wrapped_record(
        resolver,
        stage_id: str,
        task_id: str,
        commit: str,
        *,
        outputs_override: dict[str, object] | None = None,
        **kwargs,
    ):
        if stage_id == "QUALITY_INTERLOCK":
            effective_outputs = dict(valid_outputs(resolver, stage_id))
            effective_outputs["Q4_SATISFACTION"] = "DIRECT_PASS"
            if outputs_override:
                effective_outputs.update(outputs_override)
            value = original_record(
                resolver,
                stage_id,
                task_id,
                commit,
                outputs_override=effective_outputs,
                **kwargs,
            )
        else:
            value = original_record(
                resolver,
                stage_id,
                task_id,
                commit,
                **kwargs,
            )

        outputs = value["outputs"]
        assert isinstance(outputs, dict)

        if stage_id == "MODEL_DIAGNOSTIC_GPT":
            outputs.update(
                PERSPECTIVE="GPT_PERSPECTIVE",
                EXECUTION="EXECUTED",
            )
        elif stage_id == "MODEL_DIAGNOSTIC_CLAUDE":
            outputs.update(
                PERSPECTIVE="CLAUDE_PERSPECTIVE",
                EXECUTION="EXECUTED",
            )
        elif stage_id == "MODEL_DIAGNOSTIC_AGGREGATE":
            outputs.update(
                GPT_PERSPECTIVE_RESULT={"EXECUTION": "EXECUTED"},
                CLAUDE_PERSPECTIVE_RESULT={"EXECUTION": "EXECUTED"},
                ISOLATION_CHECK="PASS",
            )

        if outputs_override and stage_id != "QUALITY_INTERLOCK":
            outputs.update(outputs_override)
            if (
                stage_id == "HARBOR_LLMAJ"
                and "EXTERNAL_RUN_ID" in outputs_override
            ):
                outputs["HARBOR_RUN_ID"] = outputs_override["EXTERNAL_RUN_ID"]

        value.pop("record_id", None)
        value["record_id"] = ExecutionRecordBuilder._record_id(value)
        return value

    monkeypatch.setattr(request.module, "_temp_control_repo", wrapped_repo)
    monkeypatch.setattr(request.module, "_record", wrapped_record)
    yield
