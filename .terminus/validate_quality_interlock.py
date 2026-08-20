#!/usr/bin/env python3
"""Enforce the Edition-3 eight-agent quality interlock on durable task sessions.

This validator is additive to validate_review_freshness.py. Producer quality gates are
required before/at freeze, Q4/Q6 are mandatory packet-bound semantic gates before
Pre-LLMaJ, and both Q8 perspective simulations are mandatory before Harbor/model-backed
states. Q8 remains diagnostic and never substitutes for official model trials.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import q4_closure
import q4_human_risk
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


def _validate_human_risk_gate(
    task: str,
    truth_commit: str,
    q4_rel: str,
    gate: dict[str, str],
    report: freshness.Report,
    context: str,
) -> bool:
    if str(gate["status"]).upper() != "PASS":
        report.error(
            f"{context}: Q4 Human Risk Acceptance must be PASS before advancing"
        )
        return False
    feedback_id = q4_human_risk.feedback_id_from_evidence(gate["evidence"])
    if not feedback_id:
        report.error(
            f"{context}: Q4 Human Risk Acceptance must cite exactly one "
            "feedback_<sha256> ID"
        )
        return False
    q4_path = freshness.safe_repo_path(
        q4_rel,
        report,
        "Q4 Spec-Test Contract Reviewer",
    )
    if q4_path is None:
        return False
    q4 = freshness.load_json(q4_path, report, "Q4 Spec-Test Contract Reviewer")
    if q4 is None:
        return False
    try:
        q4_human_risk.validate_human_risk_acceptance(
            ROOT,
            envelope={
                "type": q4_human_risk.SATISFACTION_MODE,
                "feedback_id": feedback_id,
            },
            q4_result=q4,
        )
    except ValueError as exc:
        report.error(f"{context}: Q4 Human Risk Acceptance invalid: {exc}")
        return False
    if q4.get("task") != task or q4.get("task_commit") != truth_commit:
        report.error(
            f"{context}: Q4 Human Risk Acceptance does not bind the current task commit"
        )
        return False
    return True


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
        q4_satisfied = False
        q4_gate = _find_gate(gates, "q4 spec-test contract reviewer")
        if q4_gate is None:
            report.error(f"{context}: missing mandatory quality gate 'Q4 Spec-Test Contract Reviewer'")
        else:
            q4_status = str(q4_gate["status"]).upper()
            if q4_status == "PASS":
                q4_path = _validate_packet_review_gate(
                    task, truth_commit, q4_gate, "Q4 Spec-Test Contract Reviewer", "Spec-Test Contract Reviewer", report
                )
                q4_satisfied = q4_path is not None
            elif q4_status == "REVISE":
                q4_rel = freshness.review_path_from_evidence(q4_gate["evidence"])
                closure_gate = _find_gate(gates, "q4 adjudicated closure")
                risk_gate = _find_gate(gates, "q4 human risk acceptance")
                if not q4_rel:
                    report.error(f"{context}: Q4 REVISE row must cite its exact frozen review result")
                if closure_gate is not None and str(closure_gate["status"]).upper() == "PASS":
                    closure_path = _validate_packet_review_gate(
                        task, truth_commit, closure_gate, "Q4 Adjudicated Closure", "Q4 Closure Adjudicator", report
                    )
                    if closure_path is not None:
                        closure_errors, metadata = q4_closure.validate_ready_closure(
                            ROOT, str(closure_path.relative_to(ROOT))
                        )
                        for error in closure_errors:
                            report.error(f"Q4 Adjudicated Closure: {error}")
                        if not closure_errors and metadata.get("final_q4_result") != q4_rel:
                            report.error(f"{context}: closure result does not bind the Q4 REVISE evidence row")
                        q4_satisfied = not closure_errors and metadata.get("final_q4_result") == q4_rel
                elif risk_gate is not None and q4_rel:
                    q4_satisfied = _validate_human_risk_gate(
                        task,
                        truth_commit,
                        q4_rel,
                        risk_gate,
                        report,
                        context,
                    )
                else:
                    report.error(
                        f"{context}: Q4 REVISE requires Q4 Adjudicated Closure PASS "
                        "or Q4 Human Risk Acceptance PASS before advancing"
                    )
            else:
                report.error(
                    f"{context}: Q4 gate must be PASS or a frozen REVISE paired "
                    f"with adjudicated closure/authenticated human risk acceptance; "
                    f"found {q4_status}"
                )

        q6_gate = _require_ready_gate(
            gates, "q6 production logic auditor", "Q6 Production Logic Auditor", report, context
        )
        q6_path = None
        if q6_gate is not None:
            q6_path = _validate_packet_review_gate(
                task, truth_commit, q6_gate, "Q6 Production Logic Auditor", "Production Logic Auditor", report
            )

        summary = _require_ready_gate(gates, "quality interlock", "Quality Interlock", report, context)
        if summary is not None and (not q4_satisfied or q6_path is None):
            report.error(
                f"{context}: Quality Interlock PASS requires Q4 direct PASS, "
                "validated adjudicated closure, or authenticated human risk "
                "acceptance, plus current Q6 PASS"
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
