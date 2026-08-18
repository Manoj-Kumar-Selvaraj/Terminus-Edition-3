from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.quality_executor import (  # noqa: E402
    Q4_ROLE,
    Q8_ROLE,
    REVIEW_SCHEMA,
    Projection,
    QualityExecutorError,
    WorkspaceTools,
    hash_files,
    load_packet,
    minimal_prompt,
    select_backend,
    validate_review_result,
)

TASK_SHA = "a" * 40
CONTROL_SHA = "b" * 40
ROLE_HASH = "c" * 64


def _packet(role: str = Q4_ROLE) -> dict[str, object]:
    task = "quality-test"
    review_id = "quality-test-aaaaaaaa-spec-test-contract-deadbeef00"
    review_path = f".terminus/reviews/{task}/aaaaaaaa/{review_id}.json"
    return {
        "schema_version": "3.0",
        "review_id": review_id,
        "protocol_policy_version": "2.2",
        "prompt_policy_version": "2.2",
        "role_policy_version": "1.1" if role != Q8_ROLE else "1.0",
        "control_plane_commit": CONTROL_SHA,
        "role_contract_hash": ROLE_HASH,
        "task": task,
        "task_commit": TASK_SHA,
        "state": "FROZEN_CANDIDATE",
        "role": role,
        "question": "test",
        "authoritative_rules": ["TERMINUS_3_AI_INSTRUCTIONS.md"],
        "evidence_allowed": ["instruction.md", "tests/"],
        "evidence_excluded": ["previous review"],
        "prior_verdicts_visible": False,
        "isolation_mode": "PROCEDURAL",
        "output_schema": REVIEW_SCHEMA,
        "review_output_path": review_path,
    }


def _write_packet(root: Path, packet: dict[str, object]) -> Path:
    review = Path(str(packet["review_output_path"]))
    packet_path = review.with_name(review.stem + ".packet.json")
    target = root / packet_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(packet), encoding="utf-8")
    return packet_path


def test_packet_path_and_review_identity_are_bound(tmp_path: Path) -> None:
    packet = _packet()
    packet_path = _write_packet(tmp_path, packet)
    relative, loaded = load_packet(tmp_path, packet_path)
    assert relative == packet_path
    assert loaded["task_commit"] == TASK_SHA

    wrong = packet_path.with_name("wrong.packet.json")
    (tmp_path / wrong).write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(QualityExecutorError, match="does not match review_output_path"):
        load_packet(tmp_path, wrong)


def test_q_backend_selection_is_exactly_one_and_cursor_is_auto() -> None:
    packet = _packet()
    cursor = select_backend(packet, executor="cursor")
    assert cursor.executor == "cursor"
    assert cursor.provider is None
    assert cursor.model == "auto"

    with pytest.raises(QualityExecutorError, match="provider/model overrides are forbidden"):
        select_backend(packet, executor="cursor", model="anything")
    with pytest.raises(QualityExecutorError, match="exactly one provider"):
        select_backend(packet, executor="api", model="gpt-test")

    api = select_backend(packet, executor="api", provider="openai", model="gpt-test")
    assert api.executor == "api"
    assert api.provider == "openai"
    assert api.model == "gpt-test"


def test_difficulty_quality_role_is_api_only() -> None:
    with pytest.raises(QualityExecutorError, match="API-key-only"):
        select_backend(_packet(Q8_ROLE), executor="cursor")
    selected = select_backend(
        _packet(Q8_ROLE), executor="api", provider="anthropic", model="claude-test"
    )
    assert selected.provider == "anthropic"


def test_minimal_prompt_preserves_efficiency_and_freshness_constraints() -> None:
    packet_path = Path(".terminus/reviews/t/aaaaaaaa/r.packet.json")
    prompt = minimal_prompt(packet_path)
    assert packet_path.as_posix() in prompt
    assert "Minimize fresh input tokens" in prompt
    assert "Never trade correctness for efficiency" in prompt
    assert "prior review conclusions" in prompt
    assert "Persist the complete required schema-v3 result" in prompt
    assert "resume" not in prompt.lower()


def test_workspace_tools_are_read_only_except_exact_review_sink(tmp_path: Path) -> None:
    (tmp_path / "task").mkdir()
    (tmp_path / "task" / "instruction.md").write_text("alpha\nbeta\n", encoding="utf-8")
    packet_path = tmp_path / ".terminus/reviews/t/aaaaaaaa/r.packet.json"
    review_path = tmp_path / ".terminus/reviews/t/aaaaaaaa/r.json"
    packet_path.parent.mkdir(parents=True)
    packet_path.write_text("{}", encoding="utf-8")
    projection = Projection(tmp_path, packet_path, review_path, hash_files(tmp_path))
    tools = WorkspaceTools(projection)

    result = tools.grep("beta")
    assert result["matches"][0]["path"] == "task/instruction.md"
    assert tools.read_file("task/instruction.md")["total_lines"] == 2
    tools.write_review({"verdict": "REVISE"})
    with pytest.raises(QualityExecutorError, match="exactly once"):
        tools.write_review({"verdict": "PASS"})


def _projection_for_validation(tmp_path: Path) -> tuple[Projection, dict[str, object]]:
    packet = _packet()
    packet_relative = _write_packet(tmp_path, packet)
    schema = tmp_path / REVIEW_SCHEMA
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object"}',
        encoding="utf-8",
    )
    review_path = tmp_path / str(packet["review_output_path"])
    projection = Projection(
        root=tmp_path,
        packet_path=tmp_path / packet_relative,
        review_path=review_path,
        baseline=hash_files(tmp_path),
    )
    return projection, packet


def _pass_review(projection: Projection, packet: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": packet["schema_version"],
        "review_id": packet["review_id"],
        "role": packet["role"],
        "task": packet["task"],
        "task_commit": packet["task_commit"],
        "control_plane_commit": packet["control_plane_commit"],
        "protocol_policy_version": packet["protocol_policy_version"],
        "prompt_policy_version": packet["prompt_policy_version"],
        "role_policy_version": packet["role_policy_version"],
        "role_contract_hash": packet["role_contract_hash"],
        "context_packet": projection.packet_path.relative_to(projection.root).as_posix(),
        "verdict": "PASS",
        "findings": [],
        "role_output": {
            "BLOCKING_FINDING_IDS": [],
            "ADVISORY_FINDING_IDS": [],
            "EXHAUSTIVENESS": {
                "REQUIREMENTS_ENUMERATED": "COMPLETE",
                "VERIFIER_BEHAVIORS_ENUMERATED": "COMPLETE",
                "FORWARD_MATRIX_COMPLETE": "YES",
                "REVERSE_MATRIX_COMPLETE": "YES",
                "DELEGATED_CONTRACTS_COMPLETE": "YES",
                "P2P_BOUNDARIES_COMPLETE": "YES",
                "F2P_BOUNDARIES_COMPLETE": "YES",
                "OUTPUT_INTERFACES_COMPLETE": "YES",
                "SECOND_PASS_OMISSION_SWEEP": "PASS",
                "UNINSPECTED_SCOPE": [],
            },
        },
    }


def test_deterministic_validator_rejects_binding_and_side_effect_drift(tmp_path: Path) -> None:
    projection, packet = _projection_for_validation(tmp_path)
    review = _pass_review(projection, packet)
    projection.review_path.parent.mkdir(parents=True, exist_ok=True)
    projection.review_path.write_text(json.dumps(review), encoding="utf-8")
    assert validate_review_result(projection, packet)["verdict"] == "PASS"

    review["task_commit"] = "d" * 40
    projection.review_path.write_text(json.dumps(review), encoding="utf-8")
    with pytest.raises(QualityExecutorError, match="not packet-bound"):
        validate_review_result(projection, packet)

    review["task_commit"] = TASK_SHA
    projection.review_path.write_text(json.dumps(review), encoding="utf-8")
    (projection.root / "unexpected.txt").write_text("mutation", encoding="utf-8")
    with pytest.raises(QualityExecutorError, match="modified files outside"):
        validate_review_result(projection, packet)


def test_llmaj_and_official_difficulty_ci_are_api_key_only() -> None:
    workflow = (ROOT / ".github/workflows/terminus-edition-3-ci.yml").read_text(encoding="utf-8")
    assert "STB_AI_API_KEY" in workflow
    for forbidden in (
        "SNORKEL_API_KEY",
        "STB_AI_CONFIG_B64",
        "STB_ALLOW_KEY_REFRESH",
        "keys-refresh --noninteractive",
    ):
        assert forbidden not in workflow
    assert "login/config restoration/key refresh fallbacks are forbidden in CI" in workflow


def test_quality_workflow_has_single_backend_selection_and_no_cursor_resume() -> None:
    workflow = (ROOT / ".github/workflows/terminus-quality-executor.yml").read_text(
        encoding="utf-8"
    )
    assert "CURSOR_API_KEY" in workflow
    assert "OPENAI_API_KEY" in workflow
    assert "ANTHROPIC_API_KEY" in workflow
    assert "--executor cursor" in workflow
    assert "--provider openai" in workflow
    assert "--provider anthropic" in workflow
    assert "--resume" not in workflow
    assert "fallback_attempted" in workflow
