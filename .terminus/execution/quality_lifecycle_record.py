#!/usr/bin/env python3
"""Build canonical StageInvocation/StageResult envelopes from validated Q reviews.

This module does not write the execution ledger. It deterministically translates
packet-bound Q4/Q6/Q8 review evidence into the registered lifecycle stage contract;
`controller_cli.py record` remains the sole recorder/state-advancement path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from execution.authority import ExecutionAuthority
    from execution.invocation import StageInvocationBuilder
    from retrieval.models import InvocationContext
    from retrieval.policy import RetrievalPolicy
else:
    from .authority import ExecutionAuthority
    from .invocation import StageInvocationBuilder
    from retrieval.models import InvocationContext
    from retrieval.policy import RetrievalPolicy

QUALITY_INTERLOCK = "QUALITY_INTERLOCK"
Q8_GPT_STAGE = "MODEL_DIAGNOSTIC_GPT"
Q8_CLAUDE_STAGE = "MODEL_DIAGNOSTIC_CLAUDE"
Q4_ROLE = "Spec-Test Contract Reviewer"
Q6_ROLE = "Production Logic Auditor"
Q8_ROLE = "Model Perspective Difficulty Simulator"
_SHA = re.compile(r"^[0-9a-f]{40,64}$")


class QualityLifecycleRecordError(RuntimeError):
    """Fail-closed quality lifecycle envelope error."""


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityLifecycleRecordError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise QualityLifecycleRecordError(f"{label} must contain one JSON object")
    return value


def _sha256_bytes(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _run_ref(run_id: str, label: str, path: Path) -> dict[str, str]:
    digest = _sha256_bytes(path.read_bytes())
    return {
        "kind": "RUN",
        "ref": f"run:github:{run_id}-{label}#{digest}",
        "content_hash": digest,
    }


def _commit_ref(task_commit: str) -> dict[str, str]:
    """Anchor external review hashes to the immutable task snapshot they judged."""
    return {
        "kind": "COMMIT",
        "ref": f"commit:{task_commit}",
    }


def _git_result_ref(
    root: Path,
    evidence_commit: str,
    path: Path,
    review_id: str,
) -> dict[str, str]:
    """Bind a review result to exact repository bytes at the evidence commit."""
    if not _SHA.fullmatch(evidence_commit):
        raise QualityLifecycleRecordError(
            "evidence_commit must be a full hexadecimal Git commit"
        )
    root = root.resolve()
    source = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        relative = source.relative_to(root).as_posix()
    except ValueError as exc:
        raise QualityLifecycleRecordError(
            "review evidence path must be inside the repository"
        ) from exc

    raw = source.read_bytes()
    committed = subprocess.run(
        ["git", "-C", str(root), "show", f"{evidence_commit}:{relative}"],
        check=False,
        capture_output=True,
    )
    if committed.returncode != 0:
        raise QualityLifecycleRecordError(
            f"review evidence is not present at evidence_commit: {relative}"
        )
    if committed.stdout != raw:
        raise QualityLifecycleRecordError(
            f"review evidence bytes do not match evidence_commit: {relative}"
        )
    digest = _sha256_bytes(raw)
    return {
        "kind": "RESULT",
        "ref": f"git:{evidence_commit}:{relative}#{review_id}",
        "content_hash": digest,
    }


def _review_ready(review: Mapping[str, Any], role: str) -> bool:
    return (
        review.get("role") == role
        and review.get("verdict") == "PASS"
        and review.get("confidence") in {"HIGH", "MEDIUM"}
        and review.get("evidence_status") == "SUFFICIENT"
        and review.get("missing_evidence") in (None, [])
    )


def _same_binding(values: list[Mapping[str, Any]]) -> tuple[str, str, str]:
    tasks = {str(value.get("task") or "") for value in values}
    task_commits = {str(value.get("task_commit") or "") for value in values}
    control_commits = {str(value.get("control_plane_commit") or "") for value in values}
    if len(tasks) != 1 or "" in tasks:
        raise QualityLifecycleRecordError("quality artifacts do not share one task binding")
    if len(task_commits) != 1 or "" in task_commits:
        raise QualityLifecycleRecordError("quality artifacts do not share one task_commit")
    if len(control_commits) != 1 or "" in control_commits:
        raise QualityLifecycleRecordError(
            "quality artifacts do not share one control_plane_commit"
        )
    return next(iter(tasks)), next(iter(task_commits)), next(iter(control_commits))


def _build_invocation(
    root: Path,
    *,
    stage: str,
    task: str,
    task_commit: str,
    control_commit: str,
    inputs: Mapping[str, Any],
) -> dict[str, Any]:
    policy = RetrievalPolicy(root)
    authority = ExecutionAuthority(policy)
    role = authority.primary_role_for_stage(stage)
    context = InvocationContext(
        stage_id=stage,
        role_id=role,
        task_id=task,
        task_commit=task_commit,
        control_plane_commit=control_commit,
    )
    invocation = StageInvocationBuilder(root, policy).build(context, dict(inputs))
    if invocation.get("readiness") != "READY":
        raise QualityLifecycleRecordError(
            f"canonical {stage} invocation is not READY: {invocation.get('readiness')}"
        )
    return invocation


def build_interlock_envelopes(
    root: Path,
    *,
    q4_packet_path: Path,
    q4_review_path: Path,
    q6_packet_path: Path,
    q6_review_path: Path,
    run_id: str,
    evidence_commit: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    q4_packet = _load_object(q4_packet_path, "Q4 packet")
    q4 = _load_object(q4_review_path, "Q4 review")
    q6_packet = _load_object(q6_packet_path, "Q6 packet")
    q6 = _load_object(q6_review_path, "Q6 review")
    task, task_commit, control_commit = _same_binding([q4_packet, q4, q6_packet, q6])

    if q4.get("role") != Q4_ROLE or q4_packet.get("role") != Q4_ROLE:
        raise QualityLifecycleRecordError("Q4 role binding mismatch")
    if q6.get("role") != Q6_ROLE or q6_packet.get("role") != Q6_ROLE:
        raise QualityLifecycleRecordError("Q6 role binding mismatch")
    if q4.get("review_id") != q4_packet.get("review_id"):
        raise QualityLifecycleRecordError("Q4 packet/result review_id mismatch")
    if q6.get("review_id") != q6_packet.get("review_id"):
        raise QualityLifecycleRecordError("Q6 packet/result review_id mismatch")

    inputs: dict[str, Any] = {
        "FROZEN_TASK_COMMIT": task_commit,
        "Q4_CONTEXT_PACKET": q4_packet,
        "Q6_CONTEXT_PACKET": q6_packet,
    }
    scope_hash = q6.get("review_scope_hash") or q6_packet.get("review_scope_hash")
    if scope_hash:
        inputs["Q6_REVIEW_SCOPE_HASH"] = scope_hash
    invocation = _build_invocation(
        root,
        stage=QUALITY_INTERLOCK,
        task=task,
        task_commit=task_commit,
        control_commit=control_commit,
        inputs=inputs,
    )

    q4_ready = _review_ready(q4, Q4_ROLE)
    q6_ready = _review_ready(q6, Q6_ROLE)
    sufficient = (
        q4.get("evidence_status") == "SUFFICIENT"
        and q6.get("evidence_status") == "SUFFICIENT"
    )
    outputs = {
        "Q4_RESULT": q4,
        "Q4_SATISFACTION": "DIRECT_PASS" if q4_ready else "UNSATISFIED",
        "Q6_RESULT": q6,
        "EVIDENCE_SUFFICIENCY": "SUFFICIENT" if sufficient else "INSUFFICIENT",
    }
    evidence_refs: list[dict[str, str]] = [_commit_ref(task_commit)]
    if evidence_commit is not None:
        evidence_refs.extend(
            [
                _git_result_ref(
                    root,
                    evidence_commit,
                    q4_review_path,
                    str(q4["review_id"]),
                ),
                _git_result_ref(
                    root,
                    evidence_commit,
                    q6_review_path,
                    str(q6["review_id"]),
                ),
            ]
        )
    evidence_refs.extend(
        [
            _run_ref(run_id, "q4", q4_review_path),
            _run_ref(run_id, "q6", q6_review_path),
        ]
    )
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": task_commit,
        "status": "BLOCKED",
        "outputs": outputs,
        "evidence_refs": evidence_refs,
    }

    if q4_ready and q6_ready:
        result["status"] = "QUALITY_INTERLOCK_PASS"
    elif (
        not sufficient
        or q4.get("verdict") == "INSUFFICIENT_EVIDENCE"
        or q6.get("verdict") == "INSUFFICIENT_EVIDENCE"
    ):
        result["status"] = "INSUFFICIENT_EVIDENCE"
        result["route_key"] = "INSUFFICIENT_EVIDENCE"
    elif q4.get("verdict") == "REVISE":
        result["status"] = "REVISE"
        result["route_key"] = "Q4_REVISE"
    elif q6.get("verdict") == "REVISE":
        result["status"] = "REVISE"
        result["route_key"] = "Q6_REVISE"
    else:
        result["blocking_reason"] = (
            "validated Q4/Q6 artifacts do not map to a registered QUALITY_INTERLOCK outcome"
        )
    return invocation, result


def build_q8_envelopes(
    root: Path,
    *,
    stage: str,
    packet_path: Path,
    review_path: Path,
    run_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if stage not in {Q8_GPT_STAGE, Q8_CLAUDE_STAGE}:
        raise QualityLifecycleRecordError(f"unsupported Q8 lifecycle stage: {stage}")
    packet = _load_object(packet_path, "Q8 packet")
    review = _load_object(review_path, "Q8 review")
    task, task_commit, control_commit = _same_binding([packet, review])
    if packet.get("role") != Q8_ROLE or review.get("role") != Q8_ROLE:
        raise QualityLifecycleRecordError("Q8 role binding mismatch")
    if packet.get("review_id") != review.get("review_id"):
        raise QualityLifecycleRecordError("Q8 packet/result review_id mismatch")

    question = str(packet.get("question") or "").lower()
    if stage == Q8_GPT_STAGE and "gpt/codex-style" not in question:
        raise QualityLifecycleRecordError("GPT lifecycle stage received non-GPT Q8 packet")
    if stage == Q8_CLAUDE_STAGE and "claude/claude-code-style" not in question:
        raise QualityLifecycleRecordError("Claude lifecycle stage received non-Claude Q8 packet")

    invocation = _build_invocation(
        root,
        stage=stage,
        task=task,
        task_commit=task_commit,
        control_commit=control_commit,
        inputs={
            "PRE_LLMAJ_PASS": {"stage": "PRE_LLMAJ", "status": "PASS"},
            "SOLVER_VISIBLE_TASK": {"task": task, "task_commit": task_commit},
        },
    )
    role_output = review.get("role_output")
    if not isinstance(role_output, dict):
        raise QualityLifecycleRecordError("Q8 review role_output must be an object")
    required = {
        "PERSPECTIVE",
        "EXECUTION",
        "DIAGNOSTIC_SUMMARY",
        "PREDICTED_OFFICIAL_SIGNAL",
    }
    missing = sorted(required - set(role_output))
    if missing:
        raise QualityLifecycleRecordError(f"Q8 role_output missing fields: {missing}")
    execution = str(role_output.get("EXECUTION"))
    if execution not in {"EXECUTED", "SIMULATION_NOT_EXECUTED"}:
        raise QualityLifecycleRecordError(f"invalid Q8 EXECUTION value: {execution}")

    result = {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": task_commit,
        "status": execution,
        "outputs": role_output,
        "evidence_refs": [
            _commit_ref(task_commit),
            _run_ref(run_id, "q8", review_path),
        ],
    }
    return invocation, result


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--stage",
        required=True,
        choices=[QUALITY_INTERLOCK, Q8_GPT_STAGE, Q8_CLAUDE_STAGE],
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-commit")
    parser.add_argument("--packet")
    parser.add_argument("--review")
    parser.add_argument("--q4-packet")
    parser.add_argument("--q4-review")
    parser.add_argument("--q6-packet")
    parser.add_argument("--q6-review")
    parser.add_argument("--invocation-output", required=True)
    parser.add_argument("--result-output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.stage == QUALITY_INTERLOCK:
            required = (args.q4_packet, args.q4_review, args.q6_packet, args.q6_review)
            if any(value is None for value in required):
                raise QualityLifecycleRecordError(
                    "QUALITY_INTERLOCK requires Q4/Q6 packet and review paths"
                )
            invocation, result = build_interlock_envelopes(
                root,
                q4_packet_path=Path(args.q4_packet),
                q4_review_path=Path(args.q4_review),
                q6_packet_path=Path(args.q6_packet),
                q6_review_path=Path(args.q6_review),
                run_id=args.run_id,
                evidence_commit=args.evidence_commit,
            )
        else:
            if args.packet is None or args.review is None:
                raise QualityLifecycleRecordError(
                    "Q8 lifecycle recording requires --packet and --review"
                )
            invocation, result = build_q8_envelopes(
                root,
                stage=args.stage,
                packet_path=Path(args.packet),
                review_path=Path(args.review),
                run_id=args.run_id,
            )
        _write(Path(args.invocation_output), invocation)
        _write(Path(args.result_output), result)
    except (QualityLifecycleRecordError, OSError, ValueError) as exc:
        print(f"quality lifecycle record failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
