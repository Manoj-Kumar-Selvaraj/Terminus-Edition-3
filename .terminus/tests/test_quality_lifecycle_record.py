from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

import execution.quality_lifecycle_record as lifecycle  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402

TASK_SHA = "a" * 40
CONTROL_SHA = "b" * 40


def _write(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _packet(role: str, review_id: str, question: str = "") -> dict[str, object]:
    return {
        "task": "quality-test",
        "task_commit": TASK_SHA,
        "control_plane_commit": CONTROL_SHA,
        "role": role,
        "review_id": review_id,
        "question": question,
    }


def _review(role: str, review_id: str, verdict: str = "PASS") -> dict[str, object]:
    return {
        "task": "quality-test",
        "task_commit": TASK_SHA,
        "control_plane_commit": CONTROL_SHA,
        "role": role,
        "review_id": review_id,
        "verdict": verdict,
        "confidence": "HIGH",
        "evidence_status": "SUFFICIENT",
        "missing_evidence": [],
        "role_output": {},
    }


def _stub_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    def build(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"invocation_id": "inv_" + "1" * 64, "readiness": "READY"}

    monkeypatch.setattr(lifecycle, "_build_invocation", build)


def test_interlock_pass_maps_to_canonical_advance(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_invocation(monkeypatch)
    q4_id = "quality-test-aaaaaaaa-spec-test-contract-0000000000"
    q6_id = "quality-test-aaaaaaaa-production-logic-0000000000"
    q4_packet = _write(tmp_path / "q4.packet.json", _packet(lifecycle.Q4_ROLE, q4_id))
    q4_review = _write(tmp_path / "q4.json", _review(lifecycle.Q4_ROLE, q4_id))
    q6_packet = _write(tmp_path / "q6.packet.json", _packet(lifecycle.Q6_ROLE, q6_id))
    q6 = _review(lifecycle.Q6_ROLE, q6_id)
    q6["review_scope_hash"] = "c" * 64
    q6_review = _write(tmp_path / "q6.json", q6)

    invocation, result = lifecycle.build_interlock_envelopes(
        tmp_path,
        q4_packet_path=q4_packet,
        q4_review_path=q4_review,
        q6_packet_path=q6_packet,
        q6_review_path=q6_review,
        run_id="123",
    )

    assert invocation["readiness"] == "READY"
    assert result["status"] == "QUALITY_INTERLOCK_PASS"
    assert result["outputs"]["Q4_SATISFACTION"] == "DIRECT_PASS"
    assert result["outputs"]["EVIDENCE_SUFFICIENCY"] == "SUFFICIENT"
    assert len(result["evidence_refs"]) == 3
    assert result["evidence_refs"][0] == {
        "kind": "COMMIT",
        "ref": f"commit:{TASK_SHA}",
    }


def test_interlock_revise_routes_q4_then_q6(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_invocation(monkeypatch)
    q4_id = "quality-test-aaaaaaaa-spec-test-contract-0000000000"
    q6_id = "quality-test-aaaaaaaa-production-logic-0000000000"
    q4_packet = _write(tmp_path / "q4.packet.json", _packet(lifecycle.Q4_ROLE, q4_id))
    q6_packet = _write(tmp_path / "q6.packet.json", _packet(lifecycle.Q6_ROLE, q6_id))
    q6_review = _write(tmp_path / "q6.json", _review(lifecycle.Q6_ROLE, q6_id))

    q4_review = _write(tmp_path / "q4.json", _review(lifecycle.Q4_ROLE, q4_id, "REVISE"))
    _, q4_result = lifecycle.build_interlock_envelopes(
        tmp_path,
        q4_packet_path=q4_packet,
        q4_review_path=q4_review,
        q6_packet_path=q6_packet,
        q6_review_path=q6_review,
        run_id="124",
    )
    assert q4_result["status"] == "REVISE"
    assert q4_result["route_key"] == "Q4_REVISE"

    q4_review.write_text(json.dumps(_review(lifecycle.Q4_ROLE, q4_id)), encoding="utf-8")
    q6_review.write_text(json.dumps(_review(lifecycle.Q6_ROLE, q6_id, "REVISE")), encoding="utf-8")
    _, q6_result = lifecycle.build_interlock_envelopes(
        tmp_path,
        q4_packet_path=q4_packet,
        q4_review_path=q4_review,
        q6_packet_path=q6_packet,
        q6_review_path=q6_review,
        run_id="125",
    )
    assert q6_result["status"] == "REVISE"
    assert q6_result["route_key"] == "Q6_REVISE"


def test_interlock_rejects_cross_control_plane_binding(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_invocation(monkeypatch)
    q4_id = "quality-test-aaaaaaaa-spec-test-contract-0000000000"
    q6_id = "quality-test-aaaaaaaa-production-logic-0000000000"
    q4_packet = _write(tmp_path / "q4.packet.json", _packet(lifecycle.Q4_ROLE, q4_id))
    q4_review = _write(tmp_path / "q4.json", _review(lifecycle.Q4_ROLE, q4_id))
    q6_packet_value = _packet(lifecycle.Q6_ROLE, q6_id)
    q6_packet_value["control_plane_commit"] = "d" * 40
    q6_packet = _write(tmp_path / "q6.packet.json", q6_packet_value)
    q6_review = _write(tmp_path / "q6.json", _review(lifecycle.Q6_ROLE, q6_id))

    with pytest.raises(lifecycle.QualityLifecycleRecordError, match="control_plane_commit"):
        lifecycle.build_interlock_envelopes(
            tmp_path,
            q4_packet_path=q4_packet,
            q4_review_path=q4_review,
            q6_packet_path=q6_packet,
            q6_review_path=q6_review,
            run_id="126",
        )


def test_q8_perspective_maps_to_registered_stage_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _stub_invocation(monkeypatch)
    review_id = "quality-test-aaaaaaaa-difficulty-sim-gpt-0000000000"
    packet = _packet(
        lifecycle.Q8_ROLE,
        review_id,
        "In a cold GPT/Codex-style diagnostic solve, what happens?",
    )
    review = _review(lifecycle.Q8_ROLE, review_id)
    review["role_output"] = {
        "PERSPECTIVE": "GPT_PERSPECTIVE",
        "EXECUTION": "SIMULATION_NOT_EXECUTED",
        "DIAGNOSTIC_SUMMARY": "bounded diagnostic",
        "PREDICTED_OFFICIAL_SIGNAL": "USEFUL",
    }
    packet_path = _write(tmp_path / "q8.packet.json", packet)
    review_path = _write(tmp_path / "q8.json", review)

    _, result = lifecycle.build_q8_envelopes(
        tmp_path,
        stage=lifecycle.Q8_GPT_STAGE,
        packet_path=packet_path,
        review_path=review_path,
        run_id="127",
    )
    assert result["status"] == "SIMULATION_NOT_EXECUTED"
    assert result["outputs"]["PERSPECTIVE"] == "GPT_PERSPECTIVE"
    assert result["evidence_refs"][0] == {
        "kind": "COMMIT",
        "ref": f"commit:{TASK_SHA}",
    }

    with pytest.raises(lifecycle.QualityLifecycleRecordError, match="non-Claude"):
        lifecycle.build_q8_envelopes(
            tmp_path,
            stage=lifecycle.Q8_CLAUDE_STAGE,
            packet_path=packet_path,
            review_path=review_path,
            run_id="128",
        )


def test_interlock_pass_builds_real_canonical_execution_record(tmp_path: Path) -> None:
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    task = "bridge-validator"
    q4_id = "bridge-validator-aaaaaaaa-spec-test-contract-0000000000"
    q6_id = "bridge-validator-aaaaaaaa-production-logic-0000000000"

    q4_packet_value = _packet(lifecycle.Q4_ROLE, q4_id)
    q4_review_value = _review(lifecycle.Q4_ROLE, q4_id)
    q6_packet_value = _packet(lifecycle.Q6_ROLE, q6_id)
    q6_review_value = _review(lifecycle.Q6_ROLE, q6_id)
    for value in (q4_packet_value, q4_review_value, q6_packet_value, q6_review_value):
        value["task"] = task
        value["task_commit"] = head
        value["control_plane_commit"] = head

    q4_packet = _write(tmp_path / "q4.packet.json", q4_packet_value)
    q4_review = _write(tmp_path / "q4.json", q4_review_value)
    q6_packet = _write(tmp_path / "q6.packet.json", q6_packet_value)
    q6_review = _write(tmp_path / "q6.json", q6_review_value)

    invocation, result = lifecycle.build_interlock_envelopes(
        ROOT,
        q4_packet_path=q4_packet,
        q4_review_path=q4_review,
        q6_packet_path=q6_packet,
        q6_review_path=q6_review,
        run_id="9001",
    )
    record = ExecutionRecordBuilder(ROOT).build(invocation, result)

    assert invocation["readiness"] == "READY"
    assert record["stage_id"] == lifecycle.QUALITY_INTERLOCK
    assert record["status"] == "QUALITY_INTERLOCK_PASS"
    assert record["disposition"] == "ADVANCE"
    assert record["evidence_refs"][0]["ref"] == f"commit:{head}"
    assert record["task_lineage"]["task_changed"] is False
