from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.quality_backend import select_flag_backend  # noqa: E402
from execution.quality_budget import (  # noqa: E402
    QualityBudgetError,
    budget_code,
    claim_quality_budget,
    execution_limit,
)
from execution.quality_executor import (  # noqa: E402
    Q4_ROLE,
    Q6_ROLE,
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


def test_global_q_flags_choose_exactly_one_backend() -> None:
    cursor = select_flag_backend(cursor="yes", openai="no", claude="no", stb_ai="no")
    assert cursor.backend == "cursor"
    assert cursor.model is None

    stb = select_flag_backend(
        cursor="no",
        openai="no",
        claude="no",
        stb_ai="yes",
        stb_ai_model="@anthropic/claude-opus-4-8",
    )
    assert stb.backend == "stb_ai"
    assert stb.model == "@anthropic/claude-opus-4-8"

    with pytest.raises(QualityExecutorError, match="exactly one Q backend flag"):
        select_flag_backend(cursor="yes", openai="yes", claude="no", stb_ai="no")
    with pytest.raises(QualityExecutorError, match="requires an explicit model"):
        select_flag_backend(cursor="no", openai="no", claude="no", stb_ai="yes")


def test_difficulty_quality_role_is_api_only() -> None:
    with pytest.raises(QualityExecutorError, match="API-key-only"):
        select_backend(_packet(Q8_ROLE), executor="cursor")
    selected = select_backend(
        _packet(Q8_ROLE), executor="api", provider="anthropic", model="claude-test"
    )
    assert selected.provider == "anthropic"


def test_q_execution_limits_are_task_scoped_policy() -> None:
    assert execution_limit(Q4_ROLE) == 3
    assert execution_limit(Q6_ROLE) == 2
    assert execution_limit("Spec Gap Repairer") == 1
    assert execution_limit("Verifier Coverage Repairer") == 1
    assert execution_limit("Spec Ambiguity Repairer") == 1
    assert execution_limit("Oracle & Runtime Repair Specialist") == 1
    assert execution_limit("Task Format Enforcer") == 1
    assert execution_limit(Q8_ROLE) == 1


def test_q4_budget_allows_three_claims_and_rejects_fourth(tmp_path: Path) -> None:
    packet = _packet(Q4_ROLE)
    for ordinal in range(1, 4):
        claim = claim_quality_budget(
            tmp_path,
            packet,
            packet_path="packet.json",
            backend="cursor",
            run_id=str(100 + ordinal),
            run_attempt="1",
        )
        assert claim["used"] == ordinal
        assert claim["limit"] == 3
    with pytest.raises(QualityBudgetError, match="Q4 execution budget exhausted"):
        claim_quality_budget(
            tmp_path,
            packet,
            packet_path="packet.json",
            backend="cursor",
            run_id="104",
            run_attempt="1",
        )


def test_q6_budget_allows_two_and_other_q_role_only_one(tmp_path: Path) -> None:
    q6 = _packet(Q6_ROLE)
    claim_quality_budget(
        tmp_path,
        q6,
        packet_path="q6.packet.json",
        backend="stb_ai",
        run_id="201",
        run_attempt="1",
    )
    claim = claim_quality_budget(
        tmp_path,
        q6,
        packet_path="q6b.packet.json",
        backend="stb_ai",
        run_id="202",
        run_attempt="1",
    )
    assert claim["used"] == 2
    assert claim["remaining"] == 0
    with pytest.raises(QualityBudgetError, match="Q6 execution budget exhausted"):
        claim_quality_budget(
            tmp_path,
            q6,
            packet_path="q6c.packet.json",
            backend="stb_ai",
            run_id="203",
            run_attempt="1",
        )

    other = _packet("Spec Gap Repairer")
    other["task"] = "other-quality-test"
    claim_quality_budget(
        tmp_path,
        other,
        packet_path="q1.packet.json",
        backend="openai",
        run_id="301",
        run_attempt="1",
    )
    with pytest.raises(QualityBudgetError, match="Q1 execution budget exhausted"):
        claim_quality_budget(
            tmp_path,
            other,
            packet_path="q1b.packet.json",
            backend="openai",
            run_id="302",
            run_attempt="1",
        )


def test_q8_perspectives_have_distinct_one_shot_budgets(tmp_path: Path) -> None:
    gpt = _packet(Q8_ROLE)
    gpt["review_id"] = "quality-test-aaaaaaaa-difficulty-sim-gpt-deadbeef00"
    gpt["question"] = "In a cold GPT/Codex-style diagnostic solve, what happens?"
    claude = _packet(Q8_ROLE)
    claude["review_id"] = "quality-test-aaaaaaaa-difficulty-sim-claude-deadbeef00"
    claude["question"] = "In a cold Claude/Claude-Code-style diagnostic solve, what happens?"

    assert budget_code(gpt) == "q8-gpt"
    assert budget_code(claude) == "q8-claude"

    gpt_claim = claim_quality_budget(
        tmp_path,
        gpt,
        packet_path="q8-gpt.packet.json",
        backend="stb_ai",
        run_id="501",
        run_attempt="1",
    )
    claude_claim = claim_quality_budget(
        tmp_path,
        claude,
        packet_path="q8-claude.packet.json",
        backend="stb_ai",
        run_id="502",
        run_attempt="1",
    )
    assert gpt_claim["q_stage"] == "Q8-GPT"
    assert claude_claim["q_stage"] == "Q8-CLAUDE"
    assert gpt_claim["limit"] == claude_claim["limit"] == 1

    with pytest.raises(QualityBudgetError, match="Q8-GPT execution budget exhausted"):
        claim_quality_budget(
            tmp_path,
            gpt,
            packet_path="q8-gpt-2.packet.json",
            backend="stb_ai",
            run_id="503",
            run_attempt="1",
        )


def test_budget_claim_is_idempotent_for_same_github_attempt(tmp_path: Path) -> None:
    packet = _packet(Q4_ROLE)
    first = claim_quality_budget(
        tmp_path,
        packet,
        packet_path="packet.json",
        backend="cursor",
        run_id="401",
        run_attempt="1",
    )
    repeated = claim_quality_budget(
        tmp_path,
        packet,
        packet_path="packet.json",
        backend="cursor",
        run_id="401",
        run_attempt="1",
    )
    assert first["status"] == "CLAIMED"
    assert repeated["status"] == "ALREADY_CLAIMED"
    assert repeated["used"] == 1


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


def test_automatic_task_ci_is_model_free_and_never_refreshes_credentials() -> None:
    workflow = (ROOT / ".github/workflows/terminus-edition-3-ci.yml").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "STB_AI_API_KEY",
        "SNORKEL_API_KEY",
        "STB_AI_CONFIG_B64",
        "STB_ALLOW_KEY_REFRESH",
        "keys-refresh",
        "keys-set",
        "Run Harbor LLMaJ",
        "diff-gpt",
        "diff-claude",
    ):
        assert forbidden not in workflow


def test_quality_workflow_uses_global_flags_shared_stb_key_and_persistent_budget() -> None:
    workflow = (ROOT / ".github/workflows/terminus-quality-executor.yml").read_text(
        encoding="utf-8"
    )
    for flag in (
        "Q_CURSOR_ENABLED",
        "Q_OPENAI_ENABLED",
        "Q_CLAUDE_ENABLED",
        "Q_STB_AI_ENABLED",
    ):
        assert flag in workflow
    for secret in ("CURSOR_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "STB_AI_API_KEY"):
        assert secret in workflow
    assert "terminus-quality-budget" in workflow
    assert "quality_budget.py" in workflow
    assert "quality_dispatch_cli.py" in workflow
    assert "Exactly one of Q_CURSOR_ENABLED" in workflow
    assert "No login, key generation, rotation, or refresh is permitted" in workflow
    assert "keys-refresh" not in workflow
    assert "SNORKEL_API_KEY" not in workflow
    assert "--resume" not in workflow
    assert "fallback_attempted" in workflow
    assert "Resolve or generate exact review packet" in workflow
    assert ".terminus/new_review_packet.py" in workflow
    assert "packet_b64" in workflow and "review_b64" in workflow


def test_quality_lifecycle_routes_registered_q_stages_without_refresh() -> None:
    lifecycle = (ROOT / ".github/workflows/terminus-quality-lifecycle.yml").read_text(
        encoding="utf-8"
    )
    collector = (
        ROOT / ".github/workflows/terminus-quality-lifecycle-collect.yml"
    ).read_text(encoding="utf-8")
    controller = (ROOT / ".terminus/execution/controller_cli.py").read_text(encoding="utf-8")

    for stage in ("QUALITY_INTERLOCK", "MODEL_DIAGNOSTIC_GPT", "MODEL_DIAGNOSTIC_CLAUDE"):
        assert stage in lifecycle
        assert stage in controller
    for role_key in (
        "spec-test-contract",
        "production-logic",
        "difficulty-sim-gpt",
        "difficulty-sim-claude",
    ):
        assert role_key in lifecycle
    assert "uses: ./.github/workflows/terminus-quality-executor.yml" in lifecycle
    assert "secrets: inherit" in lifecycle
    assert "validate_quality_interlock.py" in lifecycle
    assert "terminus-quality-lifecycle-collect.yml" in lifecycle
    assert "GPT diagnostic received non-GPT Q8 packet" in collector
    assert "Claude diagnostic received non-Claude Q8 packet" in collector
    assert "QUALITY_LIFECYCLE_WORKFLOW" in controller
    assert "existing selected secret only; login/refresh/fallback forbidden" in controller
    for text in (lifecycle, collector, controller):
        assert "keys-refresh" not in text
        assert "SNORKEL_API_KEY" not in text
