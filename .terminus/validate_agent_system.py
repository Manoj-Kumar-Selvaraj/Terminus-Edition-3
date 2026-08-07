#!/usr/bin/env python3
"""Deterministic sanity checks for the Terminus agent/reviewer control plane."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"

REQUIRED = [
    T / "AGENT_SYSTEM.md",
    T / "CONTINUE_SESSION.md",
    T / "GOLDEN_TASKS.md",
    T / "agents" / "PROTOCOL.md",
    T / "agents" / "PROMPTS.md",
    T / "reviewers" / "PRE_LLMAJ.md",
    T / "reviewers" / "HUMAN_WRITING_CALIBRATION.md",
    T / "reviewers" / "WRITING_EXAMPLE_BANK.md",
    T / "reviewers" / "LLMAJ_LEARNING_LOG.md",
    T / "reviewers" / "REVIEWER_EVALS.md",
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
    "Stage B — independent semantic reviews",
    "Stage C — evidence sufficiency",
    "Stage D — disagreement scan",
    "Stage E — aggregate",
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
    panel = texts.get(T / "reviewers" / "PRE_LLMAJ.md", "")
    evals = texts.get(T / "reviewers" / "REVIEWER_EVALS.md", "")
    session_template = texts.get(T / "sessions" / "TEMPLATE.md", "")

    if "Agent-system policy version: `2.0`" not in agent_system:
        fail(errors, "AGENT_SYSTEM.md must declare policy version 2.0")
    if "Policy version: `2.0`" not in protocol:
        fail(errors, "agents/PROTOCOL.md must declare policy version 2.0")
    if "Prompt policy version: `2.0`" not in prompts:
        fail(errors, "agents/PROMPTS.md must declare prompt policy version 2.0")
    if "Panel policy version: `2.0`" not in panel:
        fail(errors, "reviewers/PRE_LLMAJ.md must declare panel policy version 2.0")

    for role in ROLE_HEADINGS:
        if role not in agent_system:
            fail(errors, f"AGENT_SYSTEM.md missing role: {role}")
        if role not in prompts:
            fail(errors, f"PROMPTS.md missing role prompt: {role}")

    for term in PROTOCOL_TERMS:
        if term not in protocol:
            fail(errors, f"PROTOCOL.md missing required section: {term}")

    for stage in PRE_LLMAJ_STAGES:
        if stage not in panel:
            fail(errors, f"PRE_LLMAJ.md missing required stage: {stage}")

    for required in [
        "INSUFFICIENT_EVIDENCE",
        "CONFIDENCE",
        "EVIDENCE_STATUS",
        "TASK_COMMIT",
        "PANEL_POLICY_VERSION",
        "ADJUDICATIONS",
    ]:
        if required not in panel + protocol:
            fail(errors, f"review system missing required field/term: {required}")

    case_ids = set(re.findall(r"^### ([A-Z]+-[0-9]+)\b", evals, flags=re.MULTILINE))
    if len(case_ids) < 12:
        fail(errors, f"REVIEWER_EVALS.md should contain at least 12 seed cases; found {len(case_ids)}")

    for required in [
        "Pre-LLMaJ panel",
        "Originality & Authenticity",
        "Instruction Reviewer",
        "Documentation Reviewer",
        "Harbor LLMaJ",
        "Difficulty 5x",
        "Per-test 1/5 minimum",
    ]:
        if required not in session_template:
            fail(errors, f"sessions/TEMPLATE.md missing gate: {required}")

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
    print(f"roles={len(ROLE_HEADINGS)} reviewer_eval_seed_cases={len(case_ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
