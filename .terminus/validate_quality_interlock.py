#!/usr/bin/env python3
"""Enforce the Edition-3 eight-agent quality interlock on durable task sessions.

This validator is additive to validate_review_freshness.py. Producer quality gates are
required before/at freeze, Q4/Q6 are mandatory packet-bound semantic gates before
Pre-LLMaJ, and both Q8 perspective simulations are mandatory before Harbor/model-backed
states. Q8 remains diagnostic and never substitutes for official model trials.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import validate_review_freshness as freshness
from review_contract import current_task_commit

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
SESSIONS = T / "sessions"

PRODUCER_GATES = {
    "q1 spec gap repair": "Q1 Spec Gap Repair",
    "q2 verifier coverage repair": "Q2 Verifier Coverage Repair",
    "q3 spec ambiguity repair": "Q3 Spec Ambiguity Repair",
    "q7 task format enforcer": "Q7 Task Format Enforcer",
}

INTERLOCK_GATES = {
    "q4 spec-test contract reviewer": (
        "Q4 Spec-Test Contract Reviewer",
        "Spec-Test Contract Reviewer",
    ),
    "q6 production logic auditor": (
        "Q6 Production Logic Auditor",
        "Production Logic Auditor",
    ),
}

SIMULATION_GATES = {
    "q8 gpt perspective simulation": (
        "Q8 GPT Perspective Simulation",
        "GPT_PERSPECTIVE",
        "GPT",
    ),
    "q8 claude perspective simulation": (
        "Q8 Claude Perspective Simulation",
        "CLAUDE_PERSPECTIVE",
        "Claude",
    ),
}

FREEZE_OR_LATER = {
    "FROZEN_CANDIDATE",
    "QUALITY_INTERLOCK",
    "PRE_LLMAJ",
    "LLMAJ",
    "VALIDATED",
    "DIFFICULTY_10X",
    "RECALIBRATING",
    "FINAL_AUDIT",
    "SUBMISSION_READY",
}

PRE_LLMAJ_OR_LATER = {
    "PRE_LLMAJ",
    "LLMAJ",
    "VALIDATED",
    "DIFFICULTY_10X",
    "RECALIBRATING",
    "FINAL_AUDIT",
    "SUBMISSION_READY",
}

MODEL_BACKED_STATES = {
    "LLMAJ",
    "VALIDATED",
    "DIFFICULTY_10X",
    "RECALIBRATING",
    "FINAL_AUDIT",
    "SUBMISSION_READY",
}


def set_root(root: Path) -> None:
    global ROOT, T, SESSIONS
    ROOT = root.resolve()
    T = ROOT / ".terminus"
    SESSIONS = T / "sessions"
    freshness.set_root(ROOT)


def _gate_map(session: dict) -> dict[str, dict[str, str]]:
    return {str(gate["label"]).strip().lower(): gate for gate in session.get("gates", [])}


def _find_gate(gates: dict[str, dict[str, str]], needle: str) -> dict[str, str] | None:
    for label, gate in gates.items():
        if needle in label:
            return gate
    return None


def _require_ready_gate(
    gates: dict[str, dict[str, str]],
    needle: str,
    display: str,
    report: freshness.Report,
    context: str,
) -> dict[str, str] | None:
    gate = _find_gate(gates, needle)
    if gate is None:
        report.error(f"{context}: missing mandatory quality gate '{display}'")
        return None
    if str(gate["status"]).upper() != "PASS":
        report.error(
            f"{context}: quality gate '{display}' must be PASS before advancing; "
            f"found {gate['status']}"
        )
        return None
    return gate


def _validate_packet_review_gate(
    task: str,
    truth_commit: str,
    gate: dict[str, str],
    display: str,
    role: str,
    report: freshness.Report,
) -> Path | None:
    review_rel = freshness.review_path_from_evidence(gate["evidence"])
    if not review_rel:
        report.error(
            f"{display}: PASS must cite an exact .terminus/reviews/... JSON result"
        )
        return None
    review_path = freshness.safe_repo_path(review_rel, report, display)
    if review_path is None:
        return None
    data = freshness.load_json(review_path, report, display)
    if data is None:
        return None
    freshness.validate_packet_and_review(
        review_path,
        data,
        role,
        frozenset({"PASS"}),
        task,
        truth_commit,
        report,
    )
    return review_path


def _validate_simulation_identity(
    result_path: Path,
    expected_perspective: str,
    expected_question_marker: str,
    report: freshness.Report,
) -> None:
    data = freshness.load_json(result_path, report, result_path.name)
    if data is None:
        return
    role_output = data.get("role_output", {})
    perspective = role_output.get("perspective", role_output.get("PERSPECTIVE", ""))
    if perspective and perspective != expected_perspective:
        report.error(
            f"{result_path.relative_to(ROOT)}: Q8 perspective is {perspective!r}; "
            f"expected {expected_perspective!r}"
        )

    packet_rel = str(data.get("context_packet", ""))
    packet_path = freshness.safe_repo_path(packet_rel, report, result_path.name)
    if packet_path is None:
        return
    packet = freshness.load_json(packet_path, report, result_path.name)
    if packet is None:
        return
    question = str(packet.get("question", ""))
    if expected_question_marker not in question:
        report.error(
            f"{packet_path.relative_to(ROOT)}: Q8 packet does not identify the "
            f"{expected_question_marker} perspective"
        )


def validate_session(session: dict, report: freshness.Report) -> None:
    task = str(session.get("task", ""))
    path = session.get("path")
    context = str(path.relative_to(ROOT)) if isinstance(path, Path) else task or "session"
    state = str(session.get("state", "")).upper()
    gates = _gate_map(session)

    if not task:
        report.error(f"{context}: quality interlock cannot resolve task identity")
        return

    truth_commit = current_task_commit(ROOT, task)
    if not truth_commit:
        report.error(f"{context}: cannot resolve current task commit for {task!r}")
        return

    if state in FREEZE_OR_LATER:
        for needle, display in PRODUCER_GATES.items():
            _require_ready_gate(gates, needle, display, report, context)

    if state in PRE_LLMAJ_OR_LATER:
        interlock_paths: list[Path] = []
        for needle, (display, role) in INTERLOCK_GATES.items():
            gate = _require_ready_gate(gates, needle, display, report, context)
            if gate is None:
                continue
            path_result = _validate_packet_review_gate(
                task, truth_commit, gate, display, role, report
            )
            if path_result is not None:
                interlock_paths.append(path_result)

        summary = _require_ready_gate(
            gates,
            "quality interlock",
            "Quality Interlock",
            report,
            context,
        )
        if summary is not None and len(interlock_paths) != 2:
            report.error(
                f"{context}: Quality Interlock PASS requires current packet-bound Q4 and Q6 results"
            )

    if state in MODEL_BACKED_STATES:
        simulation_paths: list[Path] = []
        for needle, (display, perspective, marker) in SIMULATION_GATES.items():
            gate = _require_ready_gate(gates, needle, display, report, context)
            if gate is None:
                continue
            path_result = _validate_packet_review_gate(
                task,
                truth_commit,
                gate,
                display,
                "Model Perspective Difficulty Simulator",
                report,
            )
            if path_result is not None:
                simulation_paths.append(path_result)
                _validate_simulation_identity(path_result, perspective, marker, report)
        if len(simulation_paths) == 2 and simulation_paths[0] == simulation_paths[1]:
            report.error(
                f"{context}: GPT and Claude perspective simulations must use distinct review executions"
            )


def validate(task: str | None = None) -> freshness.Report:
    report = freshness.Report()
    if not SESSIONS.is_dir():
        report.error(f"missing sessions directory: {SESSIONS}")
        return report

    session_files = sorted(p for p in SESSIONS.glob("*.md") if p.name != "TEMPLATE.md")
    if task:
        session_files = [path for path in session_files if path.stem == task]
        if not session_files:
            report.error(f"no session checkpoint for task '{task}'")
            return report

    for path in session_files:
        validate_session(freshness.parse_session(path), report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", help="check a single task session")
    parser.add_argument("--root", type=Path, help="repository root fixture")
    args = parser.parse_args(argv)

    if args.root:
        set_root(args.root)

    report = validate(args.task)
    for message in report.warnings:
        print(f"warning: {message}")
    for message in report.stale:
        print(f"STALE: {message}")
    for message in report.errors:
        print(f"error: {message}")

    if report.errors or report.stale:
        print(
            f"\nTerminus quality-interlock validation FAILED: "
            f"{len(report.errors)} error(s), {len(report.stale)} staleness finding(s)"
        )
        return 1

    count = len(
        [path for path in SESSIONS.glob("*.md") if path.name != "TEMPLATE.md"]
    )
    print(f"Terminus quality-interlock validation PASS (sessions={count})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
