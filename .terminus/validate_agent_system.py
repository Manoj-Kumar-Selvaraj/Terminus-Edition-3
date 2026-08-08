#!/usr/bin/env python3
"""Deterministic sanity checks for the Terminus agent/reviewer control plane."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"

REQUIRED = [
    T / "AGENT_SYSTEM.md",
    T / "CONTINUE_SESSION.md",
    T / "GOLDEN_TASKS.md",
    T / "analyze_difficulty.py",
    T / "agents" / "PROTOCOL.md",
    T / "agents" / "PROMPTS.md",
    T / "agents" / "COMPREHENSIVE_REVIEWER.md",
    T / "agents" / "schemas" / "context_packet.schema.json",
    T / "agents" / "schemas" / "review_result.schema.json",
    T / "reviewers" / "PRE_LLMAJ.md",
    T / "reviewers" / "REVIEWER_CHECKLIST.md",
    T / "reviewers" / "reviewer_criteria.json",
    T / "reviewers" / "HUMAN_WRITING_CALIBRATION.md",
    T / "reviewers" / "WRITING_EXAMPLE_BANK.md",
    T / "reviewers" / "LLMAJ_LEARNING_LOG.md",
    T / "reviewers" / "REVIEWER_EVALS.md",
    T / "reviewers" / "CALIBRATION_DATASET.md",
    T / "reviewers" / "AGENT_DESIGN_RESEARCH.md",
    T / "sessions" / "TEMPLATE.md",
]

ROLE_HEADINGS = [
    "Task Architect",
    "Verifier Engineer",
    "Compliance Auditor",
    "Difficulty Reviewer",
    "Human Quality Reviewer",
    "Instruction Writer",
    "Instruction Reviewer",
    "Documentation Writer",
    "Engineering Documentation Reviewer",
    "Originality & Authenticity Reviewer",
    "Trajectory Analyst",
    "Adjudicator",
    "CI Orchestrator / Submission Controller",
]

PROTOCOL_TERMS = [
    "Context packet",
    "Independence rules",
    "Evidence requirement",
    "Confidence and insufficient evidence",
    "Change impact and staleness",
    "Adjudication",
    "Circuit breakers",
    "Security boundaries",
    "Observability",
]

PRE_LLMAJ_STAGES = [
    "Stage A — deterministic facts",
    "Stage B — independent specialist reviews",
    "Stage C — evidence sufficiency",
    "Stage D — comprehensive checklist cold review",
    "Stage E — disagreement and omission scan",
    "Stage F — aggregate",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"SNORKEL_API_KEY\s*[:=]\s*[A-Za-z0-9_-]{16,}"),
]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def read(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        fail(errors, f"missing required file: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def main() -> int:
    errors: list[str] = []
    texts = {path: read(path, errors) for path in REQUIRED}

    agent_system = texts.get(T / "AGENT_SYSTEM.md", "")
    protocol = texts.get(T / "agents" / "PROTOCOL.md", "")
    prompts = texts.get(T / "agents" / "PROMPTS.md", "")
    comprehensive = texts.get(T / "agents" / "COMPREHENSIVE_REVIEWER.md", "")
    panel = texts.get(T / "reviewers" / "PRE_LLMAJ.md", "")
    checklist = texts.get(T / "reviewers" / "REVIEWER_CHECKLIST.md", "")
    criteria_raw = texts.get(T / "reviewers" / "reviewer_criteria.json", "")
    evals = texts.get(T / "reviewers" / "REVIEWER_EVALS.md", "")
    calibration = texts.get(T / "reviewers" / "CALIBRATION_DATASET.md", "")
    session_template = texts.get(T / "sessions" / "TEMPLATE.md", "")
    difficulty_analyzer = texts.get(T / "analyze_difficulty.py", "")

    if "Agent-system policy version: `2.2`" not in agent_system:
        fail(errors, "AGENT_SYSTEM.md must declare policy version 2.2")
    if "Policy version: `2.0`" not in protocol:
        fail(errors, "agents/PROTOCOL.md must declare policy version 2.0")
    if "Prompt policy version: `2.2`" not in prompts:
        fail(errors, "agents/PROMPTS.md must declare prompt policy version 2.2")
    if "Reviewer policy version: `1.0`" not in comprehensive:
        fail(errors, "agents/COMPREHENSIVE_REVIEWER.md must declare reviewer policy version 1.0")
    if "Panel policy version: `2.1`" not in panel:
        fail(errors, "reviewers/PRE_LLMAJ.md must declare panel policy version 2.1")
    if "Checklist snapshot version: `2026-08-08-user-supplied`" not in checklist:
        fail(errors, "REVIEWER_CHECKLIST.md must declare the current checklist snapshot")
    if "Dataset policy version: `1.0`" not in calibration:
        fail(errors, "reviewers/CALIBRATION_DATASET.md must declare dataset policy version 1.0")

    for role in ROLE_HEADINGS:
        if role not in agent_system:
            fail(errors, f"AGENT_SYSTEM.md missing role: {role}")
        if role not in prompts:
            fail(errors, f"PROMPTS.md missing role prompt: {role}")
    if "Comprehensive Reviewer" not in agent_system or "CHECKLIST_COVERAGE" not in comprehensive:
        fail(errors, "Comprehensive Reviewer must be integrated into AGENT_SYSTEM and its contract")

    for term in PROTOCOL_TERMS:
        if term not in protocol:
            fail(errors, f"PROTOCOL.md missing required section: {term}")

    for stage in PRE_LLMAJ_STAGES:
        if stage not in panel:
            fail(errors, f"PRE_LLMAJ.md missing required stage: {stage}")

    for required in [
        "CHECKLIST_COVERAGE: 100%",
        "Never stop after the first blocker",
        "POLICY_CONFLICT",
        "TEST_QUALITY_EVAL_DISPOSITIONS",
        "TRIAL_ANALYSIS_DISPOSITIONS",
    ]:
        if required.lower() not in (checklist + comprehensive + panel).lower():
            fail(errors, f"comprehensive reviewer system missing requirement: {required}")

    for required in ["INSUFFICIENT_EVIDENCE", "CONFIDENCE", "EVIDENCE_STATUS", "TASK_COMMIT", "ADJUDICATIONS"]:
        if required not in panel + protocol:
            fail(errors, f"review system missing required field/term: {required}")

    for required in [
        "Jira/Slack handoff test",
        "reverse-outline test",
        "compressed rubric",
        "information-selection problem",
    ]:
        if required.lower() not in (agent_system + prompts).lower():
            fail(errors, f"human-writing policy missing required marker: {required}")

    for required in [
        "Claude Opus 4.8 / Claude Code ×5",
        "GPT-5.5 / Codex ×5",
        "80%–<100%",
        "100%",
        "0/10",
    ]:
        if required not in agent_system:
            fail(errors, f"AGENT_SYSTEM.md missing current difficulty policy marker: {required}")

    for required in ["default=10", "partial_suite", "too_easy_reject", "expand_expected_tests"]:
        if required not in difficulty_analyzer:
            fail(errors, f"analyze_difficulty.py missing ten-run/parametrized-case support marker: {required}")

    try:
        registry = json.loads(criteria_raw) if criteria_raw else {}
    except json.JSONDecodeError as exc:
        fail(errors, f"invalid reviewer_criteria.json: {exc}")
        registry = {}

    criteria = registry.get("criteria", []) if isinstance(registry, dict) else []
    ids = [item.get("id") for item in criteria if isinstance(item, dict)]
    if len(criteria) < 60:
        fail(errors, f"reviewer criteria registry should contain at least 60 criteria; found {len(criteria)}")
    if len(ids) != len(set(ids)):
        fail(errors, "reviewer criteria registry contains duplicate IDs")
    for prefix in ["RC-INS-", "RC-ENV-", "RC-SOL-", "RC-VER-", "RC-TRIAL-", "RC-RUB-", "RC-STRUCT-", "RC-META-"]:
        if not any(str(cid).startswith(prefix) for cid in ids):
            fail(errors, f"reviewer criteria registry missing section prefix: {prefix}")
    severities = {item.get("severity") for item in criteria if isinstance(item, dict)}
    for severity in ["high", "medium", "low", "trial_medium", "informational"]:
        if severity not in severities:
            fail(errors, f"reviewer criteria registry missing severity type: {severity}")

    case_ids = set(re.findall(r"^### ([A-Z]+-[0-9]+)\b", evals, flags=re.MULTILINE))
    if len(case_ids) < 12:
        fail(errors, f"REVIEWER_EVALS.md should contain at least 12 seed cases; found {len(case_ids)}")

    for required in ["positive examples", "negative examples", "hard negatives", "hard positives", "holdout"]:
        if required.lower() not in calibration.lower():
            fail(errors, f"CALIBRATION_DATASET.md missing corpus requirement: {required}")

    for required in [
        "Pre-LLMaJ specialist panel",
        "Originality & Authenticity",
        "Instruction Reviewer",
        "Documentation Reviewer",
        "Comprehensive Reviewer",
        "Pre-LLMaJ aggregate",
        "Harbor LLMaJ",
        "Difficulty trials",
        "Per-test solvability",
        "Adjudication ledger",
        "Policy-conflict ledger",
        "Circuit breakers",
    ]:
        if required not in session_template:
            fail(errors, f"sessions/TEMPLATE.md missing gate/state section: {required}")

    schema_expectations = {
        T / "agents" / "schemas" / "context_packet.schema.json": "terminus-context-packet-v2",
        T / "agents" / "schemas" / "review_result.schema.json": "terminus-review-result-v2",
    }
    for path, expected_id in schema_expectations.items():
        raw = texts.get(path, "")
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            fail(errors, f"invalid JSON schema {path.relative_to(ROOT)}: {exc}")
            continue
        if parsed.get("$id") != expected_id:
            fail(errors, f"unexpected $id in {path.relative_to(ROOT)}")
        if parsed.get("additionalProperties") is not False:
            fail(errors, f"schema should reject undeclared top-level fields: {path.relative_to(ROOT)}")

    for path, text in texts.items():
        if not text:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                fail(errors, f"possible secret-like value in {path.relative_to(ROOT)}")

    if errors:
        print("Terminus agent-system validation FAILED:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("Terminus agent-system validation PASS")
    print(
        f"specialist_roles={len(ROLE_HEADINGS)} comprehensive_reviewer=1 "
        f"checklist_criteria={len(criteria)} reviewer_eval_seed_cases={len(case_ids)} "
        f"schemas={len(schema_expectations)} writing_policy=human_handoff_v2_2 "
        f"difficulty_policy=combined_10"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
