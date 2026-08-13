from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.authority import ExecutionAuthority  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402

CONTROL_COMMIT = subprocess.run(
    ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()


def _policy() -> RetrievalPolicy:
    return RetrievalPolicy(ROOT)


def _context(
    stage: str,
    role: str | None = None,
) -> InvocationContext:
    policy = _policy()
    resolved_role = role or ExecutionAuthority(policy).primary_role_for_stage(stage)
    return InvocationContext(
        stage_id=stage,
        role_id=resolved_role,
        control_plane_commit=CONTROL_COMMIT,
        policy_versions={"agent_system": "2.4"},
    )


def _inputs(stage: str) -> dict[str, object]:
    return {
        str(field): {"ref": f"test:{field}"}
        for field in _policy().stages[stage]["input_contract"]["required_fields"]
    }


def _walk_keys(value: object) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            result.add(str(key).lower())
            result.update(_walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_walk_keys(item))
    return result


def test_all_registered_stages_compile_from_machine_contract() -> None:
    policy = _policy()
    authority = ExecutionAuthority(policy)
    builder = StageInvocationBuilder(ROOT, policy)
    assert len(policy.stages) == 27

    for stage_id, stage in policy.stages.items():
        role = authority.primary_role_for_stage(stage_id)
        packet = builder.build(
            _context(stage_id, role),
            _inputs(stage_id),
        )
        assert packet["readiness"] == "READY", stage_id
        assert packet["stage"]["stage_id"] == stage_id
        assert packet["stage"]["role_id"] == role
        assert (
            packet["output_contract"]["allowed_status_values"]
            == stage["output_contract"]["status_values"]
        )
        assert (
            packet["routing"]["success_transition"]
            == stage["success_transition"]
        )


def test_q8_perspectives_are_separate_solver_visible_only_packets() -> None:
    builder = StageInvocationBuilder(ROOT)
    gpt = builder.build(
        _context("MODEL_DIAGNOSTIC_GPT"),
        _inputs("MODEL_DIAGNOSTIC_GPT"),
    )
    claude = builder.build(
        _context("MODEL_DIAGNOSTIC_CLAUDE"),
        _inputs("MODEL_DIAGNOSTIC_CLAUDE"),
    )

    assert gpt["evidence"]["retrieval_mode"] == "SOLVER_VISIBLE_ONLY"
    assert claude["evidence"]["retrieval_mode"] == "SOLVER_VISIBLE_ONLY"
    assert "GPT_PERSPECTIVE_RESULT" not in claude["inputs"]["required"]
    assert any(
        predicate["path"] == "PERSPECTIVE"
        and predicate["value"] == "GPT_PERSPECTIVE"
        for predicate in gpt["acceptance_predicates"]["EXECUTED"]
    )
    assert any(
        predicate["path"] == "PERSPECTIVE"
        and predicate["value"] == "CLAUDE_PERSPECTIVE"
        for predicate in claude["acceptance_predicates"]["EXECUTED"]
    )


def test_external_gate_owners_are_explicit() -> None:
    authority = ExecutionAuthority(_policy())
    assert authority.primary_role_for_stage("HARBOR_LLMAJ") == "HARBOR_LLMAJ_GATE"
    assert (
        authority.primary_role_for_stage("OFFICIAL_MODEL_TRIALS")
        == "OFFICIAL_MODEL_EVALUATION_GATE"
    )
    assert (
        authority.primary_role_for_stage("DIFFICULTY_ASSESSMENT")
        == "DIFFICULTY_REVIEWER"
    )


def test_controller_observer_cannot_execute_producer_stage() -> None:
    with pytest.raises(
        ValueError,
        match="execution role CI_ORCHESTRATOR is not authorized",
    ):
        StageInvocationBuilder(ROOT).build(
            _context("WORK_PACKAGE_RESEARCH", "CI_ORCHESTRATOR"),
            _inputs("WORK_PACKAGE_RESEARCH"),
        )


def test_creation_controller_observer_cannot_execute_a1_stage() -> None:
    with pytest.raises(
        ValueError,
        match="execution role CREATION_CONTROLLER is not authorized",
    ):
        StageInvocationBuilder(ROOT).build(
            _context("WORK_PACKAGE_RESEARCH", "CREATION_CONTROLLER"),
            _inputs("WORK_PACKAGE_RESEARCH"),
        )


def test_missing_required_inputs_produces_blocked_nonexecuting_packet() -> None:
    packet = StageInvocationBuilder(ROOT).build(
        _context("RULE_RESOLUTION"),
        {},
        retrieval_query="authority",
    )
    assert packet["readiness"] == "BLOCKED_MISSING_INPUTS"
    assert packet["missing_required_inputs"] == ["CREATION_REQUEST"]
    assert packet["retrieval"]["status"] == "SKIPPED_BLOCKED_INPUTS"


def test_undeclared_inputs_are_dropped_without_name_leakage() -> None:
    packet = StageInvocationBuilder(ROOT).build(
        _context("RULE_RESOLUTION"),
        {
            "CREATION_REQUEST": "create",
            "ORACLE_SECRET": "must-not-project",
        },
    )
    assert packet["readiness"] == "READY"
    assert packet["ignored_input_count"] == 1
    assert "ORACLE_SECRET" not in json.dumps(packet, sort_keys=True)


def test_valid_role_cannot_build_handoff_for_wrong_stage() -> None:
    with pytest.raises(ValueError, match="not authorized for stage"):
        StageInvocationBuilder(ROOT).build(
            _context(
                "DETERMINISTIC_VALIDATION",
                "Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR",
            ),
            {},
        )


def test_task_identity_requires_exact_pair() -> None:
    with pytest.raises(ValueError, match="supplied together"):
        StageInvocationBuilder(ROOT).build(
            InvocationContext(
                stage_id="RULE_RESOLUTION",
                role_id="CREATION_CONTROLLER",
                task_id="task-x",
                control_plane_commit=CONTROL_COMMIT,
            ),
            {"CREATION_REQUEST": "create"},
        )


def test_unavailable_control_plane_commit_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="not available in repository history",
    ):
        StageInvocationBuilder(ROOT).build(
            InvocationContext(
                stage_id="RULE_RESOLUTION",
                role_id="CREATION_CONTROLLER",
                control_plane_commit="f" * 40,
            ),
            {"CREATION_REQUEST": "create"},
        )


def test_stale_declared_policy_version_fails_closed() -> None:
    with pytest.raises(ValueError, match="stale policy version agent_system"):
        StageInvocationBuilder(ROOT).build(
            InvocationContext(
                stage_id="RULE_RESOLUTION",
                role_id="CREATION_CONTROLLER",
                control_plane_commit=CONTROL_COMMIT,
                policy_versions={"agent_system": "0.0"},
            ),
            {"CREATION_REQUEST": "create"},
        )


def test_invocation_identity_is_stable_and_input_bound() -> None:
    builder = StageInvocationBuilder(ROOT)
    first = builder.build(
        _context("RULE_RESOLUTION"),
        {"CREATION_REQUEST": {"goal": "one"}},
    )
    second = builder.build(
        _context("RULE_RESOLUTION"),
        {"CREATION_REQUEST": {"goal": "one"}},
    )
    changed = builder.build(
        _context("RULE_RESOLUTION"),
        {"CREATION_REQUEST": {"goal": "two"}},
    )
    assert first["invocation_id"] == second["invocation_id"]
    assert first["invocation_id"] != changed["invocation_id"]


def test_packet_has_no_private_reasoning_fields() -> None:
    packet = StageInvocationBuilder(ROOT).build(
        _context("MODEL_DIAGNOSTIC_GPT"),
        _inputs("MODEL_DIAGNOSTIC_GPT"),
    )
    forbidden = {
        "chain_of_thought",
        "reasoning",
        "scratchpad",
        "private_reasoning",
        "reasoning_chain",
    }
    assert not (_walk_keys(packet) & forbidden)


def test_missing_index_preserves_normal_chatgpt_fallback(
    tmp_path: Path,
) -> None:
    packet = StageInvocationBuilder(ROOT).build(
        _context("RULE_RESOLUTION"),
        {"CREATION_REQUEST": "create"},
        retrieval_query="policy",
        retrieval_db=tmp_path / "absent.sqlite3",
    )
    assert packet["readiness"] == "READY"
    assert packet["retrieval"]["status"] == "DIRECT_READ_FALLBACK"
    assert packet["evidence"]["mandatory_exact_reads"]


def test_unknown_evidence_restriction_fails_closed() -> None:
    with pytest.raises(
        ValueError,
        match="unknown excluded evidence classes",
    ):
        StageInvocationBuilder(ROOT).build(
            InvocationContext(
                stage_id="RULE_RESOLUTION",
                role_id="CREATION_CONTROLLER",
                control_plane_commit=CONTROL_COMMIT,
                excluded_evidence_classes=frozenset({"NOT_A_REAL_CLASS"}),
            ),
            {"CREATION_REQUEST": "create"},
        )
