from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution import controller_cli  # noqa: E402
from execution.quality_mode import (  # noqa: E402
    QualityExecutionModeError,
    inline_execution_mode,
    resolve_quality_execution_modes,
)


def _policy_root(tmp_path: Path) -> Path:
    target = tmp_path / ".terminus" / "agents"
    target.mkdir(parents=True)
    source = ROOT / ".terminus" / "agents" / "quality_execution_mode.json"
    (target / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_default_modes_are_q4_q6_automated_and_q8_off(tmp_path: Path) -> None:
    policy = resolve_quality_execution_modes(_policy_root(tmp_path))
    assert policy["q4_q6_mode"] == "AUTOMATED"
    assert policy["q8_mode"] == "OFF"
    assert policy["mandatory_quality_role_keys"] == [
        "spec-test-contract",
        "production-logic",
    ]


def test_mode_overrides_are_validated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _policy_root(tmp_path)
    monkeypatch.setenv("TERMINUS_Q4_Q6_MODE", "manual")
    monkeypatch.setenv("TERMINUS_Q8_MODE", "automated")
    policy = resolve_quality_execution_modes(root)
    assert policy["q4_q6_mode"] == "MANUAL"
    assert policy["q8_mode"] == "AUTOMATED"

    monkeypatch.setenv("TERMINUS_Q8_MODE", "invalid")
    with pytest.raises(QualityExecutionModeError, match="TERMINUS_Q8_MODE"):
        resolve_quality_execution_modes(root)


def test_inline_same_chat_roles_and_producers() -> None:
    policy = resolve_quality_execution_modes(ROOT)
    assert inline_execution_mode(
        policy, role_class="PRODUCER", role_id="A1_SCENARIO_RESEARCHER"
    ) == "INLINE_SPECIALIST"
    assert inline_execution_mode(
        policy, role_class="FIXER", role_id="Q7_TASK_FORMAT_ENFORCER"
    ) == "INLINE_SPECIALIST"
    assert inline_execution_mode(
        policy,
        role_class="REVIEWER",
        role_id="Q5_ORACLE_RUNTIME_REPAIR_SPECIALIST",
    ) == "INLINE_SPECIALIST"
    assert inline_execution_mode(
        policy, role_class="CONTROLLER", role_id="CI_ORCHESTRATOR"
    ) == "ORCHESTRATOR_DIRECT"
    assert inline_execution_mode(
        policy, role_class="REVIEWER", role_id="INSTRUCTION_REVIEWER"
    ) == "FRESH_ROLE_CHAT"


def _args(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "task_id": "quality-test",
        "q4_q6_mode": None,
        "q8_mode": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_quality_dispatch_modes() -> None:
    automated = controller_cli._quality_lifecycle_dispatch(
        ROOT, _args(q4_q6_mode="AUTOMATED"), "QUALITY_INTERLOCK"
    )
    assert automated["execution_mode"] == "AUTOMATED_QUALITY"
    assert automated["mandatory"] is True
    assert automated["inputs"]["execute_optional_q8"] is False

    manual = controller_cli._quality_lifecycle_dispatch(
        ROOT, _args(q4_q6_mode="MANUAL"), "QUALITY_INTERLOCK"
    )
    assert manual["status"] == "MANUAL_REVIEW_REQUIRED"
    assert manual["execution_mode"] == "MANUAL_INDEPENDENT_QUALITY"
    assert manual["independent"] is True

    q8_off = controller_cli._quality_lifecycle_dispatch(
        ROOT, _args(q8_mode="OFF"), "MODEL_DIAGNOSTIC_GPT"
    )
    assert q8_off["execution_mode"] == "AUTOMATED_NO_MODEL_SKIP"
    assert q8_off["model_backed_workflow"] is False
    assert q8_off["inputs"]["execute_optional_q8"] is False

    q8_auto = controller_cli._quality_lifecycle_dispatch(
        ROOT, _args(q8_mode="AUTOMATED"), "MODEL_DIAGNOSTIC_CLAUDE"
    )
    assert q8_auto["execution_mode"] == "AUTOMATED_QUALITY"
    assert q8_auto["inputs"]["execute_optional_q8"] is True

    q8_manual = controller_cli._quality_lifecycle_dispatch(
        ROOT, _args(q8_mode="MANUAL"), "MODEL_DIAGNOSTIC_CLAUDE"
    )
    assert q8_manual["execution_mode"] == "MANUAL_INDEPENDENT_QUALITY"


def test_policy_file_declares_mandatory_inline_quality_checkpoints() -> None:
    raw = json.loads(
        (ROOT / ".terminus" / "agents" / "quality_execution_mode.json").read_text(
            encoding="utf-8"
        )
    )
    assert raw["inline_same_chat"]["quality_role_ids"] == [
        "Q1_SPEC_GAP_REPAIRER",
        "Q2_VERIFIER_COVERAGE_REPAIRER",
        "Q3_SPEC_AMBIGUITY_REPAIRER",
        "Q5_ORACLE_RUNTIME_REPAIR_SPECIALIST",
        "Q7_TASK_FORMAT_ENFORCER",
    ]
