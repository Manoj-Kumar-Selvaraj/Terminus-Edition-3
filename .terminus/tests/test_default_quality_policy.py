from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIFECYCLE = ROOT / ".github/workflows/terminus-quality-lifecycle.yml"
COLLECTOR = ROOT / ".github/workflows/terminus-quality-lifecycle-collect.yml"


def test_only_q4_q6_are_model_backed_by_default() -> None:
    workflow = LIFECYCLE.read_text(encoding="utf-8")

    assert "execute_optional_q8:" in workflow
    assert "default: false" in workflow
    assert "if: inputs.stage == 'QUALITY_INTERLOCK'" in workflow
    assert "role_key: spec-test-contract" in workflow
    assert "role_key: production-logic" in workflow

    assert (
        "if: inputs.stage == 'MODEL_DIAGNOSTIC_GPT' && inputs.execute_optional_q8"
        in workflow
    )
    assert (
        "if: inputs.stage == 'MODEL_DIAGNOSTIC_CLAUDE' && inputs.execute_optional_q8"
        in workflow
    )
    assert "skip_optional_q8:" in workflow
    assert "SIMULATION_NOT_EXECUTED" in workflow
    assert "Q8 budget claim: \\`none\\`" in workflow
    assert "Default mandatory model-backed quality: \\`Q4 + Q6 only\\`" in workflow


def test_default_q8_skip_is_a_registered_advancing_no_model_status() -> None:
    outcomes = json.loads(
        (ROOT / ".terminus/agents/execution_outcomes.json").read_text(encoding="utf-8")
    )
    predicates = json.loads(
        (ROOT / ".terminus/agents/stage_acceptance_predicates.json").read_text(
            encoding="utf-8"
        )
    )

    for stage in ("MODEL_DIAGNOSTIC_GPT", "MODEL_DIAGNOSTIC_CLAUDE"):
        assert "SIMULATION_NOT_EXECUTED" in outcomes["stages"][stage]["advance_statuses"]
        checks = predicates["stages"][stage]["SIMULATION_NOT_EXECUTED"]
        assert any(
            item.get("path") == "EXECUTION"
            and item.get("op") == "eq"
            and item.get("value") == "SIMULATION_NOT_EXECUTED"
            for item in checks
        )


def test_quality_lifecycle_persists_only_durable_execution_state() -> None:
    lifecycle = LIFECYCLE.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    forbidden = 'git add -- ".terminus/executions/$TASK" ".terminus/workflows/$TASK"'

    assert forbidden not in lifecycle
    assert forbidden not in collector
    assert 'git add -- ".terminus/executions/$TASK"' in lifecycle
    assert 'git add -- ".terminus/executions/$TASK"' in collector
