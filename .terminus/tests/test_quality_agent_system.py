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
    for role in (
        "Spec-Test Contract Reviewer",
        "Production Logic Auditor",
        "Model Perspective Difficulty Simulator",
    ):
        assert contract.ROLE_POLICY_VERSIONS[role] == "1.0"
        assert role in contract.QUALITY_REVIEW_ROLES
        assert contract.ROLE_PROMPT_HEADINGS[role]


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


def test_q4_is_bidirectional_and_q6_is_not_loc_only() -> None:
    prompts = (T / "agents/QUALITY_AGENT_PROMPTS.md").read_text(encoding="utf-8")
    q4 = prompts.split("## Q4 — Spec-Test Contract Reviewer", 1)[1].split("## Q5 —", 1)[0]
    q6 = prompts.split("## Q6 — Production Logic Auditor", 1)[1].split("## Q7 —", 1)[0]
    assert "requirement -> tests" in q4
    assert "test behavior -> discoverable requirement" in q4
    assert "LOC count" in q6
    assert "reachability" in q6.lower()
    assert ">=3,000 substantive reachable" in q6
