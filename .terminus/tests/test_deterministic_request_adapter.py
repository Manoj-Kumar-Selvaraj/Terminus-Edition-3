from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.deterministic_request import (  # noqa: E402
    STAGE_ID,
    build_request,
    dispatch_envelope,
    validate_request,
)

TASK = "terraform-ansible-managed-resources"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _task_commit() -> str:
    return _git("log", "-1", "--format=%H", "--", TASK)


def test_request_is_deterministic_and_commit_bound() -> None:
    head = _git("rev-parse", "HEAD")
    task_commit = _task_commit()
    request = build_request(
        ROOT,
        task_id=TASK,
        task_commit=task_commit,
        control_plane_commit=head,
        expected_repository_head=head,
    )
    second = build_request(
        ROOT,
        task_id=TASK,
        task_commit=task_commit,
        control_plane_commit=head,
        expected_repository_head=head,
    )
    assert request == second
    assert request["request_id"].startswith("detreq_")
    assert request["stage_id"] == STAGE_ID
    assert request["task_commit"] == task_commit
    assert request["expected_repository_head"] == head
    assert request["evidence_contract"] == {
        "oracle_reward": 1,
        "nop_reward": 0,
        "require_f2p_empirical_matrix": True,
        "require_p2p_empirical_matrix": True,
    }

    validated = validate_request(ROOT, request, request_base=head)
    assert validated["request_id"] == request["request_id"]
    assert validated["task_id"] == TASK
    assert validated["task_commit"] == task_commit


def test_request_rejects_branch_base_and_contract_drift() -> None:
    head = _git("rev-parse", "HEAD")
    parent = _git("rev-parse", "HEAD^")
    request = build_request(
        ROOT,
        task_id=TASK,
        task_commit=_task_commit(),
        control_plane_commit=head,
        expected_repository_head=head,
    )
    with pytest.raises(ValueError, match="branch/base mismatch"):
        validate_request(ROOT, request, request_base=parent)

    drifted = json.loads(json.dumps(request))
    drifted["evidence_contract"]["oracle_reward"] = 0
    with pytest.raises(ValueError, match="evidence contract drift"):
        validate_request(ROOT, drifted, request_base=head)


def test_dispatch_envelope_uses_repository_write_trigger() -> None:
    head = _git("rev-parse", "HEAD")
    request = build_request(
        ROOT,
        task_id=TASK,
        task_commit=_task_commit(),
        control_plane_commit=head,
        expected_repository_head=head,
    )
    dispatch = dispatch_envelope(request)
    assert dispatch["status"] == "READY_TO_DISPATCH"
    assert dispatch["execution_mode"] == "HOSTED_DETERMINISTIC_VALIDATION"
    assert dispatch["workflow"] == ".github/workflows/terminus-deterministic-request.yml"
    assert dispatch["trigger"] == "REQUEST_BRANCH_PUSH"
    assert dispatch["branch"].startswith(f"terminus-deterministic-request/{TASK}/")
    assert dispatch["request_path"].startswith(".terminus/deterministic-requests/")
    assert dispatch["request"] == request


def test_request_workflow_runs_real_oracle_and_nop_without_model_credentials() -> None:
    workflow = (ROOT / ".github/workflows/terminus-deterministic-request.yml").read_text(
        encoding="utf-8"
    )
    for marker in (
        "terminus-deterministic-request/**",
        ".terminus/deterministic-requests/*.json",
        "deterministic_request.py validate",
        "request branch/base mismatch",
        "Task changed after deterministic request",
        "Control plane changed after deterministic request",
        "terminus3.sh oracle",
        "Oracle must score 1",
        "terminus3.sh nop",
        "NOP must score 0",
        "evidence-binding.json",
        "Upload deterministic evidence",
    ):
        assert marker in workflow
    for forbidden in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CURSOR_API_KEY",
        "STB_AI_API_KEY",
        "terminus-quality-executor.yml",
    ):
        assert forbidden not in workflow
