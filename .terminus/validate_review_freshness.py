#!/usr/bin/env python3
"""Enforce commit-bound, packet-bound and policy-bound Terminus review evidence.

Historical legacy reviews remain readable evidence. They are not revalidated against
new schemas unless a current PASS/APPROVE gate attempts to rely on them.

Exit codes: 0 clean, 1 findings, 2 usage/environment error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from review_contract import (
    ROLE_POLICY_VERSIONS,
    current_task_commit,
    policy_versions,
    role_contract_hash,
    task_tree_dirty,
    validate_schema,
)

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
SESSIONS = T / "sessions"
SCHEMAS = T / "agents" / "schemas"

SESSION_READY = {"PASS", "APPROVE", "APPROVE_WITH_NOTE"}
SPECIALIST_READY = {"PASS"}
COMPREHENSIVE_READY = {"APPROVE", "APPROVE_WITH_NOTE"}
AGGREGATE_READY = {"PASS"}

REVIEW_PATH_RE = re.compile(r"(\.terminus/reviews/[A-Za-z0-9._/\-]+\.json)")
RUN_EVIDENCE_RE = re.compile(r"\b(?:run|job|artifact)\s*[`:#-]*\s*\d+", re.IGNORECASE)
PACKAGE_EVIDENCE_RE = re.compile(r"(?:\.zip\b|package\s+sha|artifact\s*[`:#-]*\s*\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class GateSpec:
    role: str | None
    verdicts: frozenset[str]
    kind: str = "review"


SEMANTIC_GATES: dict[str, GateSpec] = {
    "task architect": GateSpec("Task Architect", frozenset(SPECIALIST_READY)),
    "verifier engineer": GateSpec("Verifier Engineer", frozenset(SPECIALIST_READY)),
    "originality": GateSpec("Originality & Authenticity Reviewer", frozenset(SPECIALIST_READY)),
    "difficulty design": GateSpec("Difficulty Reviewer", frozenset(SPECIALIST_READY)),
    "compliance pre-review": GateSpec("Compliance Auditor", frozenset(SPECIALIST_READY)),
    "instruction reviewer": GateSpec("Instruction Reviewer", frozenset(SPECIALIST_READY)),
    "documentation reviewer": GateSpec(
        "Engineering Documentation Reviewer", frozenset(SPECIALIST_READY)
    ),
    "comprehensive reviewer": GateSpec(
        "Comprehensive Reviewer", frozenset(COMPREHENSIVE_READY)
    ),
    "trial analysis": GateSpec("Trajectory Analyst", frozenset(SPECIALIST_READY)),
    "final compliance": GateSpec("Compliance Auditor", frozenset(SPECIALIST_READY)),
    "final human quality": GateSpec("Human Quality Reviewer", frozenset(SPECIALIST_READY)),
    "pre-llmaj aggregate": GateSpec(None, frozenset(AGGREGATE_READY), "aggregate"),
    "pre-llmaj specialist panel": GateSpec(None, frozenset(AGGREGATE_READY), "aggregate"),
}

CANONICAL_ALIASES: tuple[tuple[str, str], ...] = (
    ("creator complexity gate", "Creator Complexity Gate"),
    ("preflight/static", "Preflight/static"),
    ("ruff verifier", "Ruff verifier"),
    ("oracle = 1", "Oracle = 1"),
    ("nop = 0", "NOP = 0"),
    ("task architect", "Task Architect"),
    ("verifier engineer", "Verifier Engineer"),
    ("originality", "Originality & Authenticity"),
    ("difficulty design", "Difficulty design"),
    ("compliance pre-review", "Compliance pre-review"),
    ("instruction reviewer", "Instruction Reviewer"),
    ("documentation reviewer", "Documentation Reviewer"),
    ("comprehensive reviewer", "Comprehensive Reviewer"),
    ("pre-llmaj aggregate", "Pre-LLMaJ aggregate"),
    ("harbor llmaj", "Harbor LLMaJ"),
    ("difficulty trials", "Difficulty trials"),
    ("gpt-5.5 difficulty", "GPT-5.5 difficulty ×5"),
    ("claude opus 4.8 difficulty", "Claude Opus 4.8 difficulty ×5"),
    ("combined difficulty", "Combined difficulty ×10"),
    ("per-test solvability", "Per-test solvability 1/10"),
    ("trial analysis", "Trial Analysis"),
    ("final compliance", "Final Compliance"),
    ("final human quality", "Final Human Quality"),
    ("final package", "Final package"),
)

BASE_SUBMISSION_READY_GATES = {
    "Preflight/static",
    "Ruff verifier",
    "Oracle = 1",
    "NOP = 0",
    "Task Architect",
    "Verifier Engineer",
    "Originality & Authenticity",
    "Difficulty design",
    "Compliance pre-review",
    "Instruction Reviewer",
    "Documentation Reviewer",
    "Comprehensive Reviewer",
    "Pre-LLMaJ aggregate",
    "Harbor LLMaJ",
    "Difficulty trials",
    "GPT-5.5 difficulty ×5",
    "Claude Opus 4.8 difficulty ×5",
    "Combined difficulty ×10",
    "Per-test solvability 1/10",
    "Trial Analysis",
    "Final Compliance",
    "Final Human Quality",
    "Final package",
}

RUN_BOUND_GATES = {
    "Creator Complexity Gate",
    "Preflight/static",
    "Ruff verifier",
    "Oracle = 1",
    "NOP = 0",
    "Harbor LLMaJ",
    "Difficulty trials",
    "GPT-5.5 difficulty ×5",
    "Claude Opus 4.8 difficulty ×5",
    "Combined difficulty ×10",
    "Per-test solvability 1/10",
}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.stale: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def staleness(self, message: str) -> None:
        self.stale.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def set_root(root: Path) -> None:
    global ROOT, T, SESSIONS, SCHEMAS
    ROOT = root.resolve()
    T = ROOT / ".terminus"
    SESSIONS = T / "sessions"
    SCHEMAS = T / "agents" / "schemas"


def canonical_gate(label: str) -> str:
    lowered = label.strip().lower()
    for needle, canonical in CANONICAL_ALIASES:
        if needle in lowered:
            return canonical
    return label.strip()


def semantic_gate_spec(label: str) -> GateSpec | None:
    lowered = label.lower()
    # More specific labels must win over the generic compliance/originality words.
    for needle in (
        "final human quality",
        "final compliance",
        "compliance pre-review",
        "pre-llmaj aggregate",
        "pre-llmaj specialist panel",
        "comprehensive reviewer",
        "documentation reviewer",
        "instruction reviewer",
        "difficulty design",
        "verifier engineer",
        "task architect",
        "trial analysis",
        "originality",
    ):
        if needle in lowered:
            return SEMANTIC_GATES[needle]
    return None


def parse_session(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    def bullet(label: str) -> str:
        match = re.search(rf"^- {re.escape(label)}: `([^`]+)`", text, flags=re.MULTILINE)
        return match.group(1) if match else ""

    schema_match = re.search(r"Session schema version: `([^`]+)`", text)
    gates: list[dict[str, str]] = []
    in_gate_table = False
    for line in text.splitlines():
        if line.strip() == "## Current gates":
            in_gate_table = True
            continue
        if in_gate_table and line.startswith("## "):
            break
        if not in_gate_table or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in {"Gate", "---"}:
            continue
        if set(cells[0]) <= {"-", " "}:
            continue
        gates.append({"label": cells[0], "status": cells[1], "evidence": cells[2]})

    return {
        "path": path,
        "text": text,
        "schema_version": schema_match.group(1) if schema_match else "",
        "task": bullet("Task"),
        "state": bullet("Controller state"),
        "task_commit": bullet("Current task commit"),
        "policy": {
            "agent_system": bullet("Agent-system policy"),
            "prompts": bullet("Specialist prompt policy"),
            "protocol": bullet("Specialist protocol policy"),
            "panel": bullet("Pre-LLMaJ panel policy"),
            "comprehensive": bullet("Comprehensive reviewer policy"),
        },
        "gates": gates,
    }


def safe_repo_path(relative: str, report: Report, context: str) -> Path | None:
    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        report.error(f"{context}: evidence path escapes repository: {relative}")
        return None
    return candidate


def review_path_from_evidence(evidence: str) -> str:
    matches = REVIEW_PATH_RE.findall(evidence)
    for match in matches:
        if not match.endswith(".packet.json"):
            return match
    return ""


def load_json(path: Path, report: Report, context: str) -> dict | None:
    if not path.is_file():
        report.error(f"{context}: missing evidence file {path.relative_to(ROOT)}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.error(f"{context}: invalid JSON in {path.relative_to(ROOT)} ({exc})")
        return None
    if not isinstance(data, dict):
        report.error(f"{context}: {path.relative_to(ROOT)} must contain a JSON object")
        return None
    return data


def validate_packet_and_review(
    review_path: Path,
    data: dict,
    expected_role: str,
    expected_verdicts: frozenset[str],
    task: str,
    truth_commit: str,
    report: Report,
) -> None:
    rel = review_path.relative_to(ROOT)
    if data.get("schema_version") != "3.0":
        report.staleness(
            f"{rel}: legacy review schema cannot support a current PASS/APPROVE gate; rerun the role"
        )
        return

    review_schema = json.loads((SCHEMAS / "review_result.schema.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    validate_schema(data, review_schema, str(rel), problems)
    for problem in problems:
        report.error(problem)
    if problems:
        return

    if data["task"] != task:
        report.error(f"{rel}: records task {data['task']!r}, expected {task!r}")
    if data["task_commit"] != truth_commit:
        report.staleness(
            f"{rel}: reviews task commit {data['task_commit'][:12]}, current task commit is {truth_commit[:12]}"
        )
    if not data["task_commit"].startswith(review_path.parent.name):
        report.error(
            f"{rel}: filed under {review_path.parent.name}/ but records task_commit {data['task_commit'][:12]}"
        )
    if data["role"] != expected_role:
        report.error(f"{rel}: role {data['role']!r} does not match gate role {expected_role!r}")
    if data["verdict"] not in expected_verdicts:
        report.error(
            f"{rel}: verdict {data['verdict']!r} cannot support this ready gate; expected {sorted(expected_verdicts)}"
        )
    if data["confidence"] == "LOW":
        report.error(f"{rel}: LOW confidence cannot support a ready gate")
    if data["evidence_status"] != "SUFFICIENT":
        report.error(f"{rel}: evidence_status must be SUFFICIENT for a ready gate")

    versions = policy_versions(ROOT)
    if data["protocol_policy_version"] != versions["protocol"]:
        report.staleness(
            f"{rel}: protocol {data['protocol_policy_version']} is stale; current is {versions['protocol']}"
        )
    expected_role_policy = ROLE_POLICY_VERSIONS.get(expected_role, "")
    if data["role_policy_version"] != expected_role_policy:
        report.staleness(
            f"{rel}: role policy {data['role_policy_version']} is stale; current is {expected_role_policy}"
        )
    current_hash = role_contract_hash(ROOT, expected_role)
    if data["role_contract_hash"] != current_hash:
        report.staleness(
            f"{rel}: role contract hash is stale ({data['role_contract_hash'][:12]} != {current_hash[:12]})"
        )

    packet_rel = str(data["context_packet"])
    if not packet_rel.endswith(".packet.json"):
        report.error(f"{rel}: context_packet must reference a .packet.json file")
        return
    packet_path = safe_repo_path(packet_rel, report, str(rel))
    if packet_path is None:
        return
    packet = load_json(packet_path, report, str(rel))
    if packet is None:
        return

    packet_schema = json.loads((SCHEMAS / "context_packet.schema.json").read_text(encoding="utf-8"))
    packet_problems: list[str] = []
    validate_schema(packet, packet_schema, str(packet_path.relative_to(ROOT)), packet_problems)
    for problem in packet_problems:
        report.error(problem)
    if packet_problems:
        return

    pairs = {
        "review_id": "review_id",
        "task": "task",
        "task_commit": "task_commit",
        "role": "role",
        "protocol_policy_version": "protocol_policy_version",
        "prompt_policy_version": "prompt_policy_version",
        "role_policy_version": "role_policy_version",
        "control_plane_commit": "control_plane_commit",
        "role_contract_hash": "role_contract_hash",
    }
    for review_key, packet_key in pairs.items():
        if data[review_key] != packet[packet_key]:
            report.error(
                f"{rel}: {review_key} does not match context packet {packet_path.relative_to(ROOT)}"
            )
    if packet["review_output_path"] != str(rel):
        report.error(
            f"{packet_path.relative_to(ROOT)}: review_output_path is {packet['review_output_path']!r}, expected {str(rel)!r}"
        )

    if expected_role == "Comprehensive Reviewer":
        coverage = data.get("role_output", {}).get("checklist_coverage_percent")
        if coverage != 100:
            report.error(f"{rel}: Comprehensive Reviewer ready verdict requires checklist_coverage_percent=100")


def validate_aggregate(
    path: Path,
    data: dict,
    task: str,
    truth_commit: str,
    report: Report,
) -> None:
    rel = path.relative_to(ROOT)
    required = {
        "task",
        "task_commit",
        "panel_policy_version",
        "verdict",
        "review_reports",
        "open_findings",
        "policy_conflicts",
    }
    missing = sorted(required - set(data))
    if missing:
        report.error(f"{rel}: aggregate missing required fields: {', '.join(missing)}")
        return
    if data["task"] != task:
        report.error(f"{rel}: aggregate task {data['task']!r} does not match {task!r}")
    if data["task_commit"] != truth_commit:
        report.staleness(
            f"{rel}: aggregate reviews {str(data['task_commit'])[:12]}, current task commit is {truth_commit[:12]}"
        )
    if data["verdict"] not in AGGREGATE_READY:
        report.error(f"{rel}: aggregate verdict {data['verdict']!r} cannot support PASS")
    versions = policy_versions(ROOT)
    if data["panel_policy_version"] != versions["panel"]:
        report.staleness(
            f"{rel}: panel policy {data['panel_policy_version']} is stale; current is {versions['panel']}"
        )
    if data.get("open_findings"):
        report.error(f"{rel}: aggregate PASS has open_findings")
    if data.get("policy_conflicts"):
        report.error(f"{rel}: aggregate PASS has unresolved policy_conflicts")
    if not isinstance(data.get("review_reports"), dict) or not data["review_reports"]:
        report.error(f"{rel}: aggregate PASS must reference frozen review reports")


def validate_semantic_gate(
    gate: dict[str, str], task: str, truth_commit: str, report: Report
) -> None:
    spec = semantic_gate_spec(gate["label"])
    if spec is None:
        return
    status = gate["status"].upper()
    if status not in SESSION_READY:
        return
    review_rel = review_path_from_evidence(gate["evidence"])
    if not review_rel:
        report.error(
            f"gate '{gate['label']}' is {status} but does not name an exact .terminus/reviews/... JSON file"
        )
        return
    review_path = safe_repo_path(review_rel, report, gate["label"])
    if review_path is None:
        return
    data = load_json(review_path, report, gate["label"])
    if data is None:
        return
    if spec.kind == "aggregate":
        validate_aggregate(review_path, data, task, truth_commit, report)
    else:
        assert spec.role is not None
        validate_packet_and_review(
            review_path, data, spec.role, spec.verdicts, task, truth_commit, report
        )


def validate_deterministic_gate(gate: dict[str, str], report: Report) -> None:
    if gate["status"].upper() not in SESSION_READY:
        return
    canonical = canonical_gate(gate["label"])
    evidence = gate["evidence"]
    if canonical in RUN_BOUND_GATES and not RUN_EVIDENCE_RE.search(evidence):
        report.error(
            f"gate '{gate['label']}' is ready but its evidence does not contain a run/job/artifact identifier"
        )
    if canonical == "Final package" and not PACKAGE_EVIDENCE_RE.search(evidence):
        report.error(
            "gate 'Final package' is ready but evidence does not name a package ZIP, package SHA, or artifact"
        )


def strict_profile(task: str) -> bool:
    path = T / "designs" / f"{task}.json"
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return data.get("profile") == "large_system_strict"


def check_session(path: Path, report: Report) -> None:
    session = parse_session(path)
    rel = path.relative_to(ROOT)
    versions = policy_versions(ROOT)
    task = session["task"]
    if not task:
        report.error(f"{rel}: missing canonical '- Task: `<name>`' identity")
        return

    if session["schema_version"] != versions["session_schema"]:
        report.error(
            f"{rel}: session schema {session['schema_version'] or 'missing'} does not match current {versions['session_schema']}"
        )

    required_policy_fields = {
        "agent_system": "Agent-system policy",
        "prompts": "Specialist prompt policy",
        "protocol": "Specialist protocol policy",
        "panel": "Pre-LLMaJ panel policy",
        "comprehensive": "Comprehensive reviewer policy",
    }
    for key, label in required_policy_fields.items():
        declared = session["policy"].get(key, "")
        if not declared:
            report.error(f"{rel}: missing '- {label}: `<version>`' identity")
        elif declared != versions[key]:
            report.staleness(
                f"{rel}: records {label} {declared}; current is {versions[key]}"
            )

    truth = current_task_commit(ROOT, task)
    if not truth:
        report.error(f"{rel}: cannot resolve current task commit for {task!r}")
        return
    if task_tree_dirty(ROOT, task):
        report.staleness(f"{rel}: task tree {task!r} has uncommitted changes")

    declared_commit = session["task_commit"]
    if not declared_commit:
        report.error(f"{rel}: missing canonical '- Current task commit: `<sha>`' line")
    elif declared_commit != truth:
        report.staleness(
            f"{rel}: records task commit {declared_commit[:12]}, current task commit is {truth[:12]}"
        )

    for gate in session["gates"]:
        status = gate["status"].upper()
        if status in SESSION_READY and not gate["evidence"].strip():
            report.error(f"{rel}: gate '{gate['label']}' is {status} with empty evidence")
        validate_semantic_gate(gate, task, truth, report)
        validate_deterministic_gate(gate, report)

    if session["state"].upper() == "SUBMISSION_READY":
        canonical_status = {canonical_gate(g["label"]): g["status"].upper() for g in session["gates"]}
        required = set(BASE_SUBMISSION_READY_GATES)
        if strict_profile(task):
            required.add("Creator Complexity Gate")
        missing = sorted(required - set(canonical_status))
        if missing:
            report.error(
                f"{rel}: SUBMISSION_READY is missing mandatory gates: {', '.join(missing)}"
            )
        unfinished = sorted(
            gate for gate in required if canonical_status.get(gate) not in SESSION_READY
        )
        if unfinished:
            report.error(
                f"{rel}: SUBMISSION_READY has non-ready mandatory gates: {', '.join(unfinished)}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", help="check a single task session")
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help="local triage only: report staleness without failing; CI must never use it",
    )
    parser.add_argument("--root", type=Path, help="repository root fixture")
    args = parser.parse_args(argv)

    if args.root:
        set_root(args.root)
    if not SESSIONS.is_dir():
        print(f"missing sessions directory: {SESSIONS}")
        return 2

    report = Report()
    session_files = sorted(p for p in SESSIONS.glob("*.md") if p.name != "TEMPLATE.md")
    if args.task:
        session_files = [p for p in session_files if p.stem == args.task]
        if not session_files:
            print(f"no session checkpoint for task '{args.task}'")
            return 2

    for path in session_files:
        check_session(path, report)

    for message in report.warnings:
        print(f"warning: {message}")
    for message in report.stale:
        prefix = "stale (allowed locally)" if args.allow_stale else "STALE"
        print(f"{prefix}: {message}")
    for message in report.errors:
        print(f"error: {message}")

    blocking = list(report.errors)
    if not args.allow_stale:
        blocking.extend(report.stale)
    if blocking:
        print(
            f"\nTerminus review-freshness validation FAILED: {len(report.errors)} error(s), "
            f"{len(report.stale)} staleness finding(s), {len(report.warnings)} warning(s)"
        )
        return 1

    if args.allow_stale and report.stale:
        print("\n--allow-stale is local triage only; it is not acceptance evidence.")
    print(
        f"Terminus review-freshness validation PASS "
        f"(sessions={len(session_files)} warnings={len(report.warnings)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
