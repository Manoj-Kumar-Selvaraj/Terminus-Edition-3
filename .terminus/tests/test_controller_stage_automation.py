from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution import controller_stage_cli  # noqa: E402
from execution.controller_cli import _continue_payload  # noqa: E402


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _rule_invocation() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "invocation_id": "inv_" + "a" * 64,
        "readiness": "READY",
        "authority": {
            "task_id": "controller-stage-test",
            "task_commit": "b" * 40,
            "control_plane_commit": "c" * 40,
        },
        "stage": {
            "stage_id": "RULE_RESOLUTION",
            "role_id": "CREATION_CONTROLLER",
            "role_class": "CONTROLLER",
        },
        "inputs": {
            "required": {"CREATION_REQUEST": "create a test task"},
            "optional": {},
        },
        "output_contract": {
            "semantic_reviewers": [],
        },
    }


def test_rule_resolution_direct_executor_builds_schema_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(controller_stage_cli, "_run_required_validator", lambda _: None)
    result = controller_stage_cli.execute(_rule_invocation())
    assert result["schema_version"] == "1.0"
    assert result["status"] == "RULES_RESOLVED"
    assert result["output_task_commit"] == "b" * 40
    assert result["outputs"]["CONTROL_PLANE_COMMIT"] == "c" * 40
    assert result["outputs"]["CREATION_PROFILE"] == "large_system_strict"
    assert result["outputs"]["KNOWN_POLICY_CONFLICTS"] == []
    assert ".terminus/validate_agent_system.py" in result["outputs"]["ACTIVE_VALIDATORS"]
    assert ".terminus/agents/stage_contracts.json" in result["outputs"]["RULE_SOURCES"]


def test_direct_controller_executor_rejects_semantic_reviewer_stage() -> None:
    invocation = _rule_invocation()
    invocation["output_contract"] = {"semantic_reviewers": ["Some Reviewer"]}
    with pytest.raises(ValueError, match="cannot replace semantic reviewers"):
        controller_stage_cli.execute(invocation)


def test_controller_continue_returns_hosted_rule_resolution_dispatch(tmp_path: Path) -> None:
    commit = _head()
    inputs = tmp_path / "inputs.json"
    inputs.write_text(
        json.dumps(
            {
                "CREATION_REQUEST": "controller automation test",
                "REQUESTED_PROFILE": "large_system_strict",
            }
        ),
        encoding="utf-8",
    )
    args = SimpleNamespace(
        task_id="controller-stage-test",
        task_commit=commit,
        control_plane_commit=commit,
        inputs_json=str(inputs),
        query=None,
        db=None,
        retrieval_limit=10,
        max_chars=30000,
        prepare_executor=None,
    )
    snapshot = {
        "state_snapshot_id": "state_controller_stage_test",
        "next": {
            "action": "INVOKE_STAGE",
            "stage_id": "RULE_RESOLUTION",
            "primary_role_id": "CREATION_CONTROLLER",
        },
    }
    payload = _continue_payload(ROOT, args, snapshot)
    assert payload["invocation"]["readiness"] == "READY"
    assert payload["executor_handoff"] is None
    dispatch = payload["dispatch"]
    assert dispatch["controller_stage"] is True
    assert dispatch["model_backed"] is False
    assert dispatch["workflow"] == ".github/workflows/terminus-controller-stage.yml"
    assert dispatch["trigger"] == "REQUEST_BRANCH_PUSH"
    assert dispatch["branch"].startswith("terminus-controller-request/controller-stage-test/")
    assert dispatch["request"]["expected_main_sha"] == commit
    assert dispatch["request"]["task_commit"] == commit
    assert dispatch["request"]["inputs"]["CREATION_REQUEST"] == "controller automation test"


def test_controller_stage_workflow_is_non_model_and_canonical() -> None:
    workflow = (ROOT / ".github/workflows/terminus-controller-stage.yml").read_text(
        encoding="utf-8"
    )
    for marker in (
        "terminus-controller-request/**",
        ".terminus/controller-requests/*.json",
        "controller_cli.py continue",
        "controller_stage_cli.py",
        "controller_cli.py record",
        "git push origin HEAD:main",
        "main moved during controller execution",
        "Model/Q execution: `none`",
    ):
        assert marker in workflow
    for forbidden in (
        "CURSOR_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "STB_AI_API_KEY",
        "terminus-quality-executor.yml",
        "stb keys refresh",
    ):
        assert forbidden not in workflow
