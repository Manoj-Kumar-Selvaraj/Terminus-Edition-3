#!/usr/bin/env python3
"""Deterministic sanity checks for the Terminus creator/reviewer control plane."""

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
    T / "CURSOR_OPERATING.md",
    T / "GOLDEN_TASKS.md",
    T / "analyze_difficulty.py",
    T / "review_contract.py",
    T / "new_review_packet.py",
    T / "validate_review_freshness.py",
    T / "validate_task_complexity.py",
    T / "agents" / "PROTOCOL.md",
    T / "agents" / "INVOKE.md",
    T / "agents" / "PROMPTS.md",
    T / "agents" / "COMPREHENSIVE_REVIEWER.md",
    T / "agents" / "CREATION_CONTROLLER.md",
    T / "agents" / "CREATION_PIPELINE.md",
    T / "agents" / "CREATOR_AGENT_REGISTRY.md",
    T / "agents" / "CREATOR_PROMPTS.md",
    T / "agents" / "schemas" / "context_packet.schema.json",
    T / "agents" / "schemas" / "review_result.schema.json",
    T / "reviewers" / "PRE_LLMAJ.md",
    T / "reviewers" / "REVIEWER_CHECKLIST.md",
    T / "reviewers" / "reviewer_criteria.json",
    T / "reviewers" / "HUMAN_WRITING_CALIBRATION.md",
    T / "reviewers" / "WRITING_EXAMPLE_BANK.md",
    T / "reviewers" / "HUMAN_ENGINEERING_SOURCE_CORPUS.md",
    T / "reviewers" / "LLMAJ_LEARNING_LOG.md",
    T / "reviewers" / "REVIEWER_EVALS.md",
    T / "reviewers" / "CALIBRATION_DATASET.md",
    T / "reviewers" / "AGENT_DESIGN_RESEARCH.md",
    T / "reviews" / "README.md",
    T / "sessions" / "TEMPLATE.md",
]

REVIEW_ROLE_HEADINGS = [
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

CREATOR_ROLE_MARKERS = [
    "Scenario Researcher",
    "System Architect",
    "Defect Topology",
    "Reference Solution",
    "Verifier Author",
    "Human Writing",
    "Instruction Writer",
    "Documentation Writer",
    "Task Assembly",
    "Complexity Governor",
    "Authoring Failure Diagnostician",
]

PROTOCOL_MARKERS = [
    "Generated context packet",
    "Independence rules",
    "Evidence requirement",
    "Confidence and insufficient evidence",
    "Change impact and staleness",
    "Packet/result binding",
    "Adjudication",
    "Circuit breakers",
    "Security boundaries",
    "Observability",
    "Submission-ready evidence",
]

PRE_LLMAJ_STAGES = [
    "Stage A — deterministic facts",
    "Stage B — independent specialist reviews",
    "Stage C — evidence sufficiency",
    "Stage D — comprehensive checklist cold review",
    "Stage E — disagreement and omission scan",
    "Stage F — aggregate",
]

ACTIVE_POLICY_FILES = [
    T / "AGENT_SYSTEM.md",
    T / "CONTINUE_SESSION.md",
    T / "agents" / "PROTOCOL.md",
    T / "agents" / "COMPREHENSIVE_REVIEWER.md",
    T / "reviewers" / "REVIEWER_CHECKLIST.md",
    T / "reviewers" / "PRE_LLMAJ.md",
]

RETIRED_CONFLICT_PHRASES = [
    "Known conflict to preserve until explicitly resolved",
    "The existing local controller currently uses a custom five-run difficulty policy",
    "the existing local difficulty controller has a five-run policy",
    "the local difficulty controller currently uses a **5-run**",
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


def declared(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}: `([^`]+)`", text)
    return match.group(1) if match else ""


def require_declared(
    errors: list[str], text: str, path: Path, label: str, expected: str
) -> None:
    actual = declared(text, label)
    if actual != expected:
        fail(
            errors,
            f"{path.relative_to(ROOT)} must declare {label} {expected}; found {actual or 'missing'}",
        )


def main() -> int:
    errors: list[str] = []
    texts = {path: read(path, errors) for path in REQUIRED}

    agent_system_path = T / "AGENT_SYSTEM.md"
    bootstrap_path = T / "CONTINUE_SESSION.md"
    operating_path = T / "CURSOR_OPERATING.md"
    protocol_path = T / "agents" / "PROTOCOL.md"
    invoke_path = T / "agents" / "INVOKE.md"
    prompts_path = T / "agents" / "PROMPTS.md"
    comprehensive_path = T / "agents" / "COMPREHENSIVE_REVIEWER.md"
    panel_path = T / "reviewers" / "PRE_LLMAJ.md"
    checklist_path = T / "reviewers" / "REVIEWER_CHECKLIST.md"
    criteria_path = T / "reviewers" / "reviewer_criteria.json"
    session_path = T / "sessions" / "TEMPLATE.md"
    creator_registry_path = T / "agents" / "CREATOR_AGENT_REGISTRY.md"
    creator_controller_path = T / "agents" / "CREATION_CONTROLLER.md"
    creator_prompts_path = T / "agents" / "CREATOR_PROMPTS.md"
    source_corpus_path = T / "reviewers" / "HUMAN_ENGINEERING_SOURCE_CORPUS.md"

    agent_system = texts.get(agent_system_path, "")
    bootstrap = texts.get(bootstrap_path, "")
    operating = texts.get(operating_path, "")
    protocol = texts.get(protocol_path, "")
    invoke = texts.get(invoke_path, "")
    prompts = texts.get(prompts_path, "")
    comprehensive = texts.get(comprehensive_path, "")
    panel = texts.get(panel_path, "")
    checklist = texts.get(checklist_path, "")
    criteria_raw = texts.get(criteria_path, "")
    session_template = texts.get(session_path, "")
    creator_registry = texts.get(creator_registry_path, "")
    creator_controller = texts.get(creator_controller_path, "")
    creator_prompts = texts.get(creator_prompts_path, "")
    source_corpus = texts.get(source_corpus_path, "")
    difficulty_analyzer = texts.get(T / "analyze_difficulty.py", "")
    packet_generator = texts.get(T / "new_review_packet.py", "")
    freshness = texts.get(T / "validate_review_freshness.py", "")
    complexity = texts.get(T / "validate_task_complexity.py", "")
    review_contract = texts.get(T / "review_contract.py", "")
    evals = texts.get(T / "reviewers" / "REVIEWER_EVALS.md", "")
    calibration = texts.get(T / "reviewers" / "CALIBRATION_DATASET.md", "")

    require_declared(errors, agent_system, agent_system_path, "Agent-system policy version", "2.3")
    require_declared(errors, bootstrap, bootstrap_path, "Bootstrap policy version", "2.2")
    require_declared(errors, operating, operating_path, "Operating policy version", "1.1")
    require_declared(errors, protocol, protocol_path, "Policy version", "2.1")
    require_declared(errors, invoke, invoke_path, "Invocation policy version", "1.1")
    require_declared(errors, prompts, prompts_path, "Prompt policy version", "2.2")
    require_declared(errors, comprehensive, comprehensive_path, "Reviewer policy version", "1.0")
    require_declared(errors, panel, panel_path, "Panel policy version", "2.2")
    require_declared(errors, session_template, session_path, "Session schema version", "2.4")
    require_declared(errors, creator_registry, creator_registry_path, "Registry version", "1.0")
    require_declared(errors, creator_controller, creator_controller_path, "Policy version", "1.0")
    require_declared(errors, creator_prompts, creator_prompts_path, "Creator prompt policy version", "1.0")
    require_declared(errors, source_corpus, source_corpus_path, "Corpus version", "1.0")

    if "Checklist snapshot version: `2026-08-08-user-supplied`" not in checklist:
        fail(errors, "REVIEWER_CHECKLIST.md must declare the current checklist snapshot")
    if "Dataset policy version: `1.0`" not in calibration:
        fail(errors, "CALIBRATION_DATASET.md must declare dataset policy version 1.0")

    for role in REVIEW_ROLE_HEADINGS:
        if role not in agent_system:
            fail(errors, f"AGENT_SYSTEM.md missing reviewer/controller role marker: {role}")
        if role not in prompts:
            fail(errors, f"PROMPTS.md missing role prompt: {role}")

    creator_text = creator_registry + creator_controller + creator_prompts
    for marker in CREATOR_ROLE_MARKERS:
        if marker.lower() not in creator_text.lower():
            fail(errors, f"creator system missing role marker: {marker}")

    for marker in PROTOCOL_MARKERS:
        if marker.lower() not in protocol.lower():
            fail(errors, f"PROTOCOL.md missing required section/marker: {marker}")

    for stage in PRE_LLMAJ_STAGES:
        if stage not in panel:
            fail(errors, f"PRE_LLMAJ.md missing required stage: {stage}")

    for path in ACTIVE_POLICY_FILES:
        text = texts.get(path, "")
        for phrase in RETIRED_CONFLICT_PHRASES:
            if phrase in text:
                fail(
                    errors,
                    f"{path.relative_to(ROOT)} still contains retired 5-vs-10 conflict wording: {phrase!r}",
                )

    difficulty_text = "\n".join([agent_system, protocol, panel, difficulty_analyzer])
    for marker in [
        "GPT-5.5",
        "Claude Opus 4.8",
        "10",
        "100%",
        "0/10",
    ]:
        if marker not in difficulty_text:
            fail(errors, f"combined-ten difficulty system missing marker: {marker}")
    for marker in ["default=10", "partial_suite", "too_easy_reject", "expand_expected_tests"]:
        if marker not in difficulty_analyzer:
            fail(errors, f"analyze_difficulty.py missing marker: {marker}")

    provenance_text = "\n".join(
        [protocol, invoke, packet_generator, freshness, review_contract, operating]
    )
    for marker in [
        "role_contract_hash",
        "control_plane_commit",
        "context_packet",
        "review_output_path",
        "PROCEDURAL",
        "STALE",
        "SUBMISSION_READY",
    ]:
        if marker.lower() not in provenance_text.lower():
            fail(errors, f"review provenance system missing marker: {marker}")

    if len(re.findall(r'^    "[a-z-]+": \{$', packet_generator, flags=re.MULTILINE)) < 11:
        fail(errors, "new_review_packet.py must define all 11 reviewable role packets")

    for marker in [
        "Final Human Quality",
        "Final Compliance",
        "Trial Analysis",
        "BASE_SUBMISSION_READY_GATES",
        "COMPREHENSIVE_READY",
        "AGGREGATE_READY",
    ]:
        if marker not in freshness:
            fail(errors, f"validate_review_freshness.py missing readiness marker: {marker}")

    for marker in [
        "large_system_strict",
        "duplicated_environment_files",
        "cross_cluster_pairs",
        "classification drift",
        "per_requirement",
    ]:
        if marker not in complexity:
            fail(errors, f"validate_task_complexity.py missing authenticity marker: {marker}")

    strict_docs = "\n".join([agent_system, creator_registry, creator_controller, creator_prompts])
    for marker in ["3,000", "30–50", "20–30", "25–30", "SCENARIO_TOO_SMALL"]:
        if marker not in strict_docs:
            fail(errors, f"strict large-system authoring policy missing marker: {marker}")

    writing_text = agent_system + prompts + creator_prompts + source_corpus
    for marker in [
        "Jira/Slack handoff",
        "reverse-outline",
        "compressed",
        "information selection",
    ]:
        if marker.lower() not in writing_text.lower():
            fail(errors, f"human-writing policy missing marker: {marker}")
    for marker in ["8 entries", "4 ecosystems"]:
        if marker.lower() not in source_corpus.lower() + creator_prompts.lower():
            fail(errors, f"human source-corpus calibration missing marker: {marker}")

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
    for prefix in [
        "RC-INS-",
        "RC-ENV-",
        "RC-SOL-",
        "RC-VER-",
        "RC-TRIAL-",
        "RC-RUB-",
        "RC-STRUCT-",
        "RC-META-",
    ]:
        if not any(str(value).startswith(prefix) for value in ids):
            fail(errors, f"reviewer criteria registry missing section prefix: {prefix}")
    severities = {item.get("severity") for item in criteria if isinstance(item, dict)}
    for severity in ["high", "medium", "low", "trial_medium", "informational"]:
        if severity not in severities:
            fail(errors, f"reviewer criteria registry missing severity: {severity}")

    case_ids = set(re.findall(r"^### ([A-Z]+-[0-9]+)\b", evals, flags=re.MULTILINE))
    if len(case_ids) < 12:
        fail(errors, f"REVIEWER_EVALS.md should contain at least 12 seed cases; found {len(case_ids)}")

    for marker in ["positive examples", "negative examples", "hard negatives", "hard positives", "holdout"]:
        if marker.lower() not in calibration.lower():
            fail(errors, f"CALIBRATION_DATASET.md missing corpus requirement: {marker}")

    for marker in [
        "Current task commit",
        "Specialist protocol policy",
        "Pre-LLMaJ specialist panel",
        "Pre-LLMaJ aggregate",
        "Harbor LLMaJ",
        "Difficulty trials",
        "Per-test solvability",
        "Trial Analysis",
        "Final Compliance",
        "Final Human Quality",
        "Final package",
        "Circuit breakers",
    ]:
        if marker not in session_template:
            fail(errors, f"sessions/TEMPLATE.md missing gate/state marker: {marker}")

    schema_expectations = {
        T / "agents" / "schemas" / "context_packet.schema.json": "terminus-context-packet-v3",
        T / "agents" / "schemas" / "review_result.schema.json": "terminus-review-result-v3",
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
            fail(errors, f"unexpected $id in {path.relative_to(ROOT)}: {parsed.get('$id')!r}")
        if parsed.get("additionalProperties") is not False:
            fail(errors, f"schema must reject undeclared top-level fields: {path.relative_to(ROOT)}")
        required = set(parsed.get("required", []))
        if path.name == "context_packet.schema.json":
            for field in [
                "role_contract_hash",
                "control_plane_commit",
                "review_output_path",
                "isolation_mode",
            ]:
                if field not in required:
                    fail(errors, f"context packet schema missing required provenance field: {field}")
        else:
            for field in [
                "role_contract_hash",
                "control_plane_commit",
                "context_packet",
                "role_output",
            ]:
                if field not in required:
                    fail(errors, f"review-result schema missing required provenance field: {field}")

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
        f"review_roles={len(REVIEW_ROLE_HEADINGS)} creator_markers={len(CREATOR_ROLE_MARKERS)} "
        f"checklist_criteria={len(criteria)} reviewer_eval_seed_cases={len(case_ids)} "
        "schemas=v3 provenance=packet_bound writing_policy=human_handoff "
        "difficulty_policy=combined_10 complexity_policy=strict_plus_authenticity"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
