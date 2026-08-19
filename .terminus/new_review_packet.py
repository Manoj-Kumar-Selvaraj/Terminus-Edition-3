#!/usr/bin/env python3
"""Generate one immutable, commit-bound context packet for a specialist review."""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

from review_contract import (
    ROLE_POLICY_VERSIONS,
    control_plane_commit,
    current_task_commit,
    governing_policy_dirty,
    policy_versions,
    role_contract_hash,
    review_scope_hash,
    task_tree_dirty,
    validate_schema,
)

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"

COMMON_RULES = [
    "TERMINUS_3_AI_INSTRUCTIONS.md",
    ".terminus/AGENT_SYSTEM.md",
    ".terminus/agents/PROTOCOL.md",
    ".terminus/agents/PROMPTS.md",
]

QUALITY_RULES = [
    ".terminus/agents/QUALITY_AGENT_REGISTRY.md",
    ".terminus/agents/QUALITY_AGENT_PROMPTS.md",
]

WRITER_HIDDEN = [
    "solution/",
    "tests/ bodies",
    "private defect IDs in .terminus/designs/",
]

ROLES: dict[str, dict[str, object]] = {
    "task-architect": {
        "role": "Task Architect",
        "question": "Is the scenario, contract and failure topology a fair, realistic, coupled engineering problem?",
        "allowed": [
            "task.toml",
            "instruction.md",
            "environment/",
            "solver-visible contracts",
            "requirement-to-test summary",
        ],
        "excluded": [
            "previous Task Architect verdict",
            "other specialist verdicts",
            "desired difficulty label",
        ],
    },
    "verifier-engineer": {
        "role": "Verifier Engineer",
        "question": "Does the verifier measure every solver-visible requirement semantically, deterministically and without easy gaming?",
        "allowed": [
            "instruction.md",
            "solver-visible contracts",
            "tests/",
            "environment/",
            "Oracle and NOP results",
        ],
        "excluded": ["other specialist verdicts", "author rationale for test design"],
    },
    "originality": {
        "role": "Originality & Authenticity Reviewer",
        "question": "Is the task original and organically constructed rather than a renamed or recombined benchmark?",
        "allowed": [
            "instruction.md",
            "environment topology",
            "verifier scenario summary",
            ".terminus/GOLDEN_TASKS.md",
            "public references",
        ],
        "excluded": [
            "creator uniqueness rationale",
            "previous originality verdict",
            "other specialist verdicts",
        ],
    },
    "difficulty-design": {
        "role": "Difficulty Reviewer",
        "question": "Is the difficulty genuine coupled reasoning rather than clerical volume or obscurity?",
        "allowed": [
            "instruction.md",
            "environment/",
            "solution/",
            "tests/",
            "trial evidence when post-trial",
        ],
        "excluded": ["desired tier", "previous difficulty verdict", "other specialist verdicts"],
    },
    "compliance": {
        "role": "Compliance Auditor",
        "question": "Would this task be rejected for a current Edition 3 structural, environment, security, metadata or packaging rule?",
        "allowed": [
            "full task tree",
            "task.toml",
            "Dockerfiles",
            "tests/",
            "static and preflight output",
        ],
        "excluded": ["other specialist verdicts", "obsolete schema from golden or public tasks"],
    },
    "instruction": {
        "role": "Instruction Reviewer",
        "question": "Is instruction.md a fair, concise, selective human engineering ticket with no ambiguity or leakage?",
        "allowed": [
            "instruction.md",
            "documents instruction.md references",
            "requirement-to-test summary",
            ".terminus/reviewers/HUMAN_WRITING_CALIBRATION.md",
            ".terminus/reviewers/WRITING_EXAMPLE_BANK.md",
        ],
        "excluded": [
            *WRITER_HIDDEN,
            "Instruction Writer rationale",
            "previous Instruction Reviewer verdict",
        ],
    },
    "documentation": {
        "role": "Engineering Documentation Reviewer",
        "question": "Are README and the difficulty, solution and verification explanations supported, natural and useful to a reviewer?",
        "allowed": [
            "README.md",
            "task.toml explanations",
            "verifier behavior summary",
            "writing calibration files",
        ],
        "excluded": ["Documentation Writer rationale", "previous Documentation verdict"],
    },
    "human-quality": {
        "role": "Human Quality Reviewer",
        "question": "Does the submission prose carry material AI cadence, boilerplate, inflated claims or leakage?",
        "allowed": [
            "all solver-facing prose",
            "README.md",
            "submission explanations",
            "writing calibration files",
        ],
        "excluded": ["writer self-explanations", "previous writing-review verdicts"],
    },
    "comprehensive-checklist": {
        "role": "Comprehensive Reviewer",
        "question": "After an independent walk of every checklist criterion, what is the checklist-level recommendation?",
        "allowed": [
            "full task tree",
            ".terminus/reviewers/REVIEWER_CHECKLIST.md",
            ".terminus/reviewers/reviewer_criteria.json",
            "static, Oracle and NOP evidence",
            "trial evidence when available",
        ],
        "excluded": [
            "all specialist verdicts until this walk is frozen",
            "previous comprehensive result for this task version",
        ],
    },
    "trajectory": {
        "role": "Trajectory Analyst",
        "question": "Why did solver attempts succeed or fail, and which layer owns remediation?",
        "allowed": [
            "trial logs and trajectories",
            "per-test statuses",
            "instruction and environment at the trial commit",
        ],
        "excluded": ["desired difficulty outcome"],
    },
    "adjudication": {
        "role": "Adjudicator",
        "question": "Which frozen review is controlling for the disputed finding, and on what rule or evidence?",
        "allowed": [
            "authoritative rules",
            "disputed artifact",
            "frozen reviewer reports",
            "run evidence",
        ],
        "excluded": ["a desired verdict", "reviews that are not yet frozen"],
    },
    "q4-closure-adjudication": {
        "role": "Q4 Closure Adjudicator",
        "question": "Does the final frozen Q4 leave any legitimately controlling blocker after the frozen adjudicated closure boundary?",
        "allowed": [
            "current authoritative rules",
            "frozen boundary adjudication",
            "final frozen Q4",
            "exact final-repair task diff",
        ],
        "excluded": [
            "desired closure outcome",
            "task edits or proposed fixes",
            "unfrozen reviewer opinions",
        ],
    },
    "spec-test-contract": {
        "role": "Spec-Test Contract Reviewer",
        "question": "Is every substantive verifier behavior discoverable from the solver-visible contract, every material requirement tested, and every grading-relevant statement unambiguous?",
        "allowed": [
            "instruction.md",
            "all solver-visible contracts referenced by instruction.md",
            "tests/",
            "test map when needed to identify classification only",
            "environment interfaces required to interpret observable behavior",
        ],
        "excluded": [
            "Q1/Q2/Q3 conclusions before the independent matrix is frozen",
            "Verifier Author coverage rationale",
            "previous Spec-Test Contract Reviewer verdict",
            "other specialist verdicts",
            "desired aggregate outcome",
        ],
        "quality": True,
    },
    "production-logic": {
        "role": "Production Logic Auditor",
        "question": "Is the solver-visible core genuinely complex, reachable, coupled, non-toy and credible as production logic rather than LOC or module padding?",
        "allowed": [
            "task.toml",
            "solver-visible environment/runtime/configuration code",
            "entrypoints and operator workflows",
            "runtime-authenticity and complexity reports",
            "representative data/state and incident evidence",
        ],
        "excluded": [
            "Complexity Governor verdict as a conclusion to copy",
            "creator claims that code is production-grade",
            "previous Production Logic Auditor verdict",
            "other specialist verdicts",
            "desired difficulty tier",
        ],
        "quality": True,
    },
    "difficulty-sim-gpt": {
        "role": "Model Perspective Difficulty Simulator",
        "question": "In a cold GPT/Codex-style diagnostic solve, what strategy, shortcuts, first divergence and likely difficulty signal emerge? This is simulation, not official GPT evidence.",
        "allowed": [
            "solver-visible task workspace only before solve",
            "normal task tools/runtime",
            "final verifier outcome only after the simulated solve is frozen",
        ],
        "excluded": [
            "solution/",
            "hidden tests before solve",
            "private defect graph/test map",
            "previous solver trajectories",
            "Claude-perspective result",
            "desired tier",
        ],
        "quality": True,
    },
    "difficulty-sim-claude": {
        "role": "Model Perspective Difficulty Simulator",
        "question": "In a cold Claude/Claude-Code-style diagnostic solve, what strategy, shortcuts, first divergence and likely difficulty signal emerge? This is simulation, not official Claude evidence.",
        "allowed": [
            "solver-visible task workspace only before solve",
            "normal task tools/runtime",
            "final verifier outcome only after the simulated solve is frozen",
        ],
        "excluded": [
            "solution/",
            "hidden tests before solve",
            "private defect graph/test map",
            "previous solver trajectories",
            "GPT-perspective result",
            "desired tier",
        ],
        "quality": True,
    },
}

GENERIC_ROLES = {
    key: spec for key, spec in ROLES.items() if key != "q4-closure-adjudication"
}


def session_state(task: str) -> str:
    path = T / "sessions" / f"{task}.md"
    if not path.is_file():
        return ""
    match = re.search(
        r"^- Controller state: `([^`]+)`",
        path.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    return match.group(1) if match else ""


def build(
    task: str,
    role_key: str,
    state: str,
    change: str,
    commit: str,
    review_id: str | None = None,
) -> dict:
    spec = ROLES[role_key]
    role = str(spec["role"])
    versions = policy_versions(ROOT)
    plane_commit = control_plane_commit(ROOT)
    contract_hash = role_contract_hash(ROOT, role)
    review_id = review_id or f"{task}-{commit[:8]}-{role_key}-{uuid.uuid4().hex[:10]}"
    output_path = f".terminus/reviews/{task}/{commit[:8]}/{review_id}.json"
    authoritative_rules = list(COMMON_RULES)
    if bool(spec.get("quality")):
        authoritative_rules.extend(QUALITY_RULES)
    packet = {
        "schema_version": "3.0",
        "review_id": review_id,
        "protocol_policy_version": versions["protocol"],
        "prompt_policy_version": versions["prompts"],
        "role_policy_version": ROLE_POLICY_VERSIONS[role],
        "control_plane_commit": plane_commit,
        "role_contract_hash": contract_hash,
        "task": task,
        "task_commit": commit,
        "state": state,
        "role": role,
        "question": str(spec["question"]),
        "authoritative_rules": authoritative_rules,
        "evidence_allowed": list(spec["allowed"]),
        "evidence_excluded": list(spec["excluded"]),
        "prior_verdicts_visible": False,
        "isolation_mode": "PROCEDURAL",
        "change_since_last_review": change,
        "output_schema": ".terminus/agents/schemas/review_result.schema.json",
        "review_output_path": output_path,
    }
    scope_hash = review_scope_hash(ROOT, task, role)
    if scope_hash:
        packet["review_scope_hash"] = scope_hash
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", help="top-level task directory name")
    parser.add_argument("role", choices=sorted(GENERIC_ROLES), help="specialist role to invoke")
    parser.add_argument("--state", help="controller state; defaults to the session checkpoint")
    parser.add_argument(
        "--change",
        default="",
        help="what changed since the last review of this dimension",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="show",
        help="print the packet instead of writing it",
    )
    args = parser.parse_args(argv)

    if not (ROOT / args.task / "task.toml").is_file():
        print(f"error: no task at {args.task}/task.toml")
        return 2

    commit = current_task_commit(ROOT, args.task)
    if not commit:
        print(f"error: cannot resolve a commit for '{args.task}'")
        return 2
    if task_tree_dirty(ROOT, args.task):
        print(
            f"refused: '{args.task}' has uncommitted changes, so a review cannot be bound "
            "to a commit. Commit the task tree first."
        )
        return 1

    role = str(ROLES[args.role]["role"])
    if governing_policy_dirty(ROOT, role):
        print(
            f"refused: governing policy/calibration files for {role} are uncommitted. "
            "Commit the control-plane policy before generating review evidence."
        )
        return 1

    state = args.state or session_state(args.task) or "PRE_LLMAJ"
    packet = build(args.task, args.role, state, args.change, commit)

    schema_path = T / "agents" / "schemas" / "context_packet.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    validate_schema(packet, schema, "packet", problems)
    if problems:
        print("refused: generated packet does not satisfy context_packet.schema.json")
        for problem in problems:
            print(f"- {problem}")
        return 1

    rendered = json.dumps(packet, indent=2) + "\n"
    if args.show:
        print(rendered, end="")
        return 0

    review_path = ROOT / packet["review_output_path"]
    packet_path = review_path.with_suffix(".packet.json")
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    if packet_path.exists() or review_path.exists():
        print(f"refused: immutable review ID already exists: {packet['review_id']}")
        return 1
    packet_path.write_text(rendered, encoding="utf-8")
    print(f"wrote {packet_path.relative_to(ROOT)}")
    print(f"review_output={review_path.relative_to(ROOT)}")
    print(
        f"role={packet['role']} task_commit={commit[:12]} "
        f"role_contract={packet['role_contract_hash'][:12]} isolation=PROCEDURAL"
    )
    if packet.get("review_scope_hash"):
        print(f"review_scope={packet['review_scope_hash'][:12]}")
    print("Open a new chat for this role and use this packet as the first review context.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
