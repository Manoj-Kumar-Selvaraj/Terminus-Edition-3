from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

import execution.chat_human_interlock as bridge  # noqa: E402

TASK = "risk-task"
CURRENT = "c" * 40
FROZEN = "a" * 40
CONTROL = "b" * 40
DECISION = "hd_" + "d" * 64


def _write(path: Path, value: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _quality_files(root: Path) -> tuple[Path, Path]:
    q4_id = f"{TASK}-aaaaaaaa-spec-test-contract-0000000000"
    q6_id = f"{TASK}-aaaaaaaa-production-logic-0000000000"
    review_dir = root / ".terminus" / "reviews" / TASK / "aaaaaaaa"
    q4_packet = {
        "task": TASK,
        "task_commit": FROZEN,
        "control_plane_commit": "1" * 40,
        "role": bridge.Q4_ROLE,
        "review_id": q4_id,
    }
    q6_packet = {
        "task": TASK,
        "task_commit": FROZEN,
        "control_plane_commit": "1" * 40,
        "role": bridge.Q6_ROLE,
        "review_id": q6_id,
        "review_scope_hash": "scope",
    }
    q4_packet_path = _write(review_dir / f"{q4_id}.packet.json", q4_packet)
    q6_packet_path = _write(review_dir / f"{q6_id}.packet.json", q6_packet)
    q4 = {
        **q4_packet,
        "context_packet": q4_packet_path.relative_to(root).as_posix(),
        "verdict": "REVISE",
        "confidence": "HIGH",
        "evidence_status": "SUFFICIENT",
        "missing_evidence": [],
        "role_output": {"BLOCKING_FINDING_IDS": ["F01"]},
    }
    q6 = {
        **q6_packet,
        "context_packet": q6_packet_path.relative_to(root).as_posix(),
        "verdict": "PASS",
        "confidence": "HIGH",
        "evidence_status": "SUFFICIENT",
        "missing_evidence": [],
    }
    return (
        _write(review_dir / f"{q4_id}.json", q4),
        _write(review_dir / f"{q6_id}.json", q6),
    )


def _stubs(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    seen: list[dict[str, object]] = []
    monkeypatch.setattr(bridge, "current_task_commit", lambda root, task: CURRENT)
    monkeypatch.setattr(bridge, "review_scope_hash", lambda root, task, role: "scope")

    def validate(root, *, envelope, q4_result):
        seen.append({"envelope": envelope, "q4": q4_result})
        return {"satisfaction": bridge.SATISFACTION_MODE}

    monkeypatch.setattr(bridge, "validate_chat_human_risk_acceptance", validate)

    class Authority:
        def __init__(self, policy):
            pass

        def primary_role_for_stage(self, stage):
            return "CI_ORCHESTRATOR"

    class InvocationBuilder:
        def __init__(self, root, policy):
            pass

        def build(self, context, inputs):
            assert context.task_commit == CURRENT
            assert context.control_plane_commit == CONTROL
            assert inputs["FROZEN_TASK_COMMIT"] == CURRENT
            assert inputs["Q6_REVIEW_SCOPE_HASH"] == "scope"
            return {"invocation_id": "inv_" + "1" * 64, "readiness": "READY"}

    monkeypatch.setattr(bridge, "ExecutionAuthority", Authority)
    monkeypatch.setattr(bridge, "StageInvocationBuilder", InvocationBuilder)
    monkeypatch.setattr(bridge, "RetrievalPolicy", lambda root: object())
    monkeypatch.setattr(
        bridge,
        "_result_ref",
        lambda root, commit, path, review_id: {
            "kind": "RESULT",
            "ref": f"git:{commit}:{path.name}#{review_id}",
            "content_hash": "sha256:" + "2" * 64,
        },
    )
    monkeypatch.setattr(
        bridge,
        "_run_ref",
        lambda run_id, label, path: {
            "kind": "RUN",
            "ref": f"run:github:{run_id}-{label}#sha256:{'3' * 64}",
            "content_hash": "sha256:" + "3" * 64,
        },
    )
    return seen


def test_builds_pass_without_rewriting_q4(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    q4, q6 = _quality_files(tmp_path)
    seen = _stubs(monkeypatch)
    invocation, result = bridge.build_chat_human_interlock(
        tmp_path,
        task_id=TASK,
        accepted_task_commit=CURRENT,
        control_plane_commit=CONTROL,
        decision_id=DECISION,
        q4_review_path=q4,
        q6_review_path=q6,
        evidence_commit="e" * 40,
        source_run_id="123",
    )

    assert invocation["readiness"] == "READY"
    assert result["status"] == "QUALITY_INTERLOCK_PASS"
    assert result["output_task_commit"] == CURRENT
    assert result["outputs"]["Q4_RESULT"]["verdict"] == "REVISE"
    assert result["outputs"]["Q4_SATISFACTION"] == "CHAT_HUMAN_RISK_ACCEPTANCE"
    assert result["outputs"]["Q4_CLOSURE_RESULT"] == {
        "type": "CHAT_HUMAN_RISK_ACCEPTANCE",
        "decision_id": DECISION,
    }
    assert result["outputs"]["Q6_RESULT"]["verdict"] == "PASS"
    assert seen[0]["envelope"]["decision_id"] == DECISION


def test_rejects_stale_q6_scope(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    q4, q6 = _quality_files(tmp_path)
    _stubs(monkeypatch)
    monkeypatch.setattr(bridge, "review_scope_hash", lambda root, task, role: "changed")
    with pytest.raises(bridge.ChatHumanInterlockError, match="review_scope_hash"):
        bridge.build_chat_human_interlock(
            tmp_path,
            task_id=TASK,
            accepted_task_commit=CURRENT,
            control_plane_commit=CONTROL,
            decision_id=DECISION,
            q4_review_path=q4,
            q6_review_path=q6,
            evidence_commit="e" * 40,
            source_run_id="123",
        )


def test_rejects_stale_current_task(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    q4, q6 = _quality_files(tmp_path)
    _stubs(monkeypatch)
    monkeypatch.setattr(bridge, "current_task_commit", lambda root, task: "f" * 40)
    with pytest.raises(bridge.ChatHumanInterlockError, match="current task snapshot"):
        bridge.build_chat_human_interlock(
            tmp_path,
            task_id=TASK,
            accepted_task_commit=CURRENT,
            control_plane_commit=CONTROL,
            decision_id=DECISION,
            q4_review_path=q4,
            q6_review_path=q6,
            evidence_commit="e" * 40,
            source_run_id="123",
        )


def test_workflow_is_request_branch_and_cas_bound() -> None:
    text = (ROOT / ".github" / "workflows" / "terminus-chat-human-interlock.yml").read_text(
        encoding="utf-8"
    )
    assert "terminus-human-interlock/**" in text
    assert ".terminus/human-interlock-requests/*.json" in text
    assert "controller_cli.py record" in text
    assert "git push origin HEAD:main" in text
    assert "main moved in task authority scope" in text
