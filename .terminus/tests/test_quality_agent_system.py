"""Regression coverage for the eight-agent Edition-3 quality interlock."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quality_registry_defines_exactly_eight_quality_agents() -> None:
    text = (T / "agents/QUALITY_AGENT_REGISTRY.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## (Q[1-8]) — ", text, flags=re.MULTILINE)
    assert headings == [f"Q{i}" for i in range(1, 9)]


def test_quality_prompts_define_every_quality_agent() -> None:
    text = (T / "agents/QUALITY_AGENT_PROMPTS.md").read_text(encoding="utf-8")
    for index in range(1, 9):
        assert f"## Q{index} — " in text


def test_creator_pipeline_routes_all_quality_agents() -> None:
    registry = (T / "agents/CREATOR_AGENT_REGISTRY.md").read_text(encoding="utf-8")
    controller = (T / "agents/CREATION_CONTROLLER.md").read_text(encoding="utf-8")
    pipeline = (T / "agents/CREATION_PIPELINE.md").read_text(encoding="utf-8")
    combined = registry + controller + pipeline
    for index in range(1, 9):
        assert f"Q{index}" in combined
    assert "QUALITY_INTERLOCK" in controller
    assert "QUALITY_INTERLOCK_PASS" in pipeline
    assert "Q4 Spec-Test Contract Reviewer" in combined
    assert "Q6 Production Logic Auditor" in combined


def test_packet_generator_exposes_independent_quality_review_packets() -> None:
    packet = _load_module("quality_packet_generator", T / "new_review_packet.py")
    assert packet.ROLES["spec-test-contract"]["role"] == "Spec-Test Contract Reviewer"
    assert packet.ROLES["production-logic"]["role"] == "Production Logic Auditor"
    assert (
        packet.ROLES["difficulty-sim-gpt"]["role"]
        == "Model Perspective Difficulty Simulator"
    )
    assert (
        packet.ROLES["difficulty-sim-claude"]["role"]
        == "Model Perspective Difficulty Simulator"
    )


def test_quality_review_roles_have_provenance_contract_versions() -> None:
    contract = _load_module("quality_review_contract", T / "review_contract.py")
    expected = {
        "Spec-Test Contract Reviewer": "1.1",
        "Production Logic Auditor": "1.1",
        "Model Perspective Difficulty Simulator": "1.0",
    }
    for role, version in expected.items():
        assert contract.ROLE_POLICY_VERSIONS[role] == version
        assert role in contract.QUALITY_REVIEW_ROLES
        assert contract.ROLE_PROMPT_HEADINGS[role]


def test_q6_is_only_scope_reusable_quality_role() -> None:
    contract = _load_module("quality_scope_contract", T / "review_contract.py")
    assert contract.SCOPE_REUSABLE_ROLES == {"Production Logic Auditor"}
    task = "jetstream-regional-stream-continuity"
    q6_hash = contract.review_scope_hash(ROOT, task, "Production Logic Auditor")
    assert len(q6_hash) == 64
    assert contract.review_scope_hash(ROOT, task, "Spec-Test Contract Reviewer") == ""


def test_difficulty_perspectives_are_isolated_and_non_official() -> None:
    packet = _load_module("quality_packet_isolation", T / "new_review_packet.py")
    gpt = packet.ROLES["difficulty-sim-gpt"]
    claude = packet.ROLES["difficulty-sim-claude"]
    assert "Claude-perspective result" in gpt["excluded"]
    assert "GPT-perspective result" in claude["excluded"]
    assert "solution/" in gpt["excluded"] and "solution/" in claude["excluded"]
    assert "not official GPT evidence" in gpt["question"]
    assert "not official Claude evidence" in claude["question"]


def test_spec_gap_agent_forbids_test_dump_wording() -> None:
    registry = (T / "agents/QUALITY_AGENT_REGISTRY.md").read_text(encoding="utf-8")
    q1 = registry.split("## Q1 — Spec Gap Repairer", 1)[1].split("## Q2 —", 1)[0]
    assert "dump test cases" in q1
    assert "one sentence per test" in q1
    assert "reverse-outline" in q1.lower()


def test_q4_is_exhaustive_bidirectional_and_q6_is_not_loc_only() -> None:
    prompts = (T / "agents/QUALITY_AGENT_PROMPTS.md").read_text(encoding="utf-8")
    q4 = prompts.split("## Q4 — Spec-Test Contract Reviewer", 1)[1].split("## Q5 —", 1)[0]
    q6 = prompts.split("## Q6 — Production Logic Auditor", 1)[1].split("## Q7 —", 1)[0]
    assert "Map every material requirement ->" in q4
    assert "Map every substantive verifier behavior ->" in q4
    assert "second adversarial omission sweep" in q4
    assert "BLOCKING_FINDING_IDS" in q4
    assert "EXHAUSTIVENESS" in q4
    assert "Finding one reason for `REVISE` is never permission to stop" in q4
    assert "LOC count" in q6
    assert "reachability" in q6.lower()
    assert ">=3,000 substantive reachable" in q6
    assert "review_scope_hash" in q6


def test_protocol_has_no_drip_adjudication_rule() -> None:
    protocol = (T / "agents/PROTOCOL.md").read_text(encoding="utf-8")
    assert "LATENT_REVIEWER_OMISSION" in protocol
    assert "one consolidated repair/refreeze cycle" in protocol
    assert ".terminus/classify_review_delta.py" in protocol


def test_quality_interlock_validator_accepts_current_pre_freeze_sessions() -> None:
    quality = _load_module("quality_interlock_current", T / "validate_quality_interlock.py")
    report = quality.validate()
    assert report.errors == []
    assert report.stale == []


def test_frozen_candidate_cannot_skip_producer_quality_gates() -> None:
    quality = _load_module("quality_interlock_freeze", T / "validate_quality_interlock.py")
    original = quality.current_task_commit
    quality.current_task_commit = lambda root, task: "a" * 40
    try:
        report = quality.freshness.Report()
        quality.validate_session(
            {
                "path": ROOT / ".terminus/sessions/fake-task.md",
                "task": "fake-task",
                "state": "FROZEN_CANDIDATE",
                "gates": [],
            },
            report,
        )
    finally:
        quality.current_task_commit = original
    joined = "\n".join(report.errors)
    for gate in (
        "Q1 Spec Gap Repair",
        "Q2 Verifier Coverage Repair",
        "Q3 Spec Ambiguity Repair",
        "Q7 Task Format Enforcer",
    ):
        assert gate in joined


def test_pre_llmaj_cannot_skip_q4_q6_quality_interlock() -> None:
    quality = _load_module("quality_interlock_prellmaj", T / "validate_quality_interlock.py")
    original = quality.current_task_commit
    quality.current_task_commit = lambda root, task: "b" * 40
    producer_gates = [
        {"label": display, "status": "PASS", "evidence": "producer evidence"}
        for display in quality.PRODUCER_GATES.values()
    ]
    try:
        report = quality.freshness.Report()
        quality.validate_session(
            {
                "path": ROOT / ".terminus/sessions/fake-task.md",
                "task": "fake-task",
                "state": "PRE_LLMAJ",
                "gates": producer_gates,
            },
            report,
        )
    finally:
        quality.current_task_commit = original
    joined = "\n".join(report.errors)
    assert "Q4 Spec-Test Contract Reviewer" in joined
    assert "Q6 Production Logic Auditor" in joined
    assert "Quality Interlock" in joined


def test_model_backed_states_require_both_q8_perspectives() -> None:
    quality = _load_module("quality_interlock_model", T / "validate_quality_interlock.py")
    original = quality.current_task_commit
    quality.current_task_commit = lambda root, task: "c" * 40
    try:
        report = quality.freshness.Report()
        quality.validate_session(
            {
                "path": ROOT / ".terminus/sessions/fake-task.md",
                "task": "fake-task",
                "state": "LLMAJ",
                "gates": [],
            },
            report,
        )
    finally:
        quality.current_task_commit = original
    joined = "\n".join(report.errors)
    assert "Q8 GPT Perspective Simulation" in joined
    assert "Q8 Claude Perspective Simulation" in joined
