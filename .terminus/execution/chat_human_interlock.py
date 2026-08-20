#!/usr/bin/env python3
"""Record QUALITY_INTERLOCK from exact Q4/Q6 evidence plus a resolved same-chat risk decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from execution.authority import ExecutionAuthority
    from execution.invocation import StageInvocationBuilder
    from q4_chat_human_risk import (
        SATISFACTION_MODE,
        validate_chat_human_risk_acceptance,
    )
    from retrieval.models import InvocationContext
    from retrieval.policy import RetrievalPolicy
    from review_contract import current_task_commit, review_scope_hash
else:
    from .authority import ExecutionAuthority
    from .invocation import StageInvocationBuilder
    from q4_chat_human_risk import (
        SATISFACTION_MODE,
        validate_chat_human_risk_acceptance,
    )
    from retrieval.models import InvocationContext
    from retrieval.policy import RetrievalPolicy
    from review_contract import current_task_commit, review_scope_hash

QUALITY_INTERLOCK = "QUALITY_INTERLOCK"
Q4_ROLE = "Spec-Test Contract Reviewer"
Q6_ROLE = "Production Logic Auditor"


class ChatHumanInterlockError(RuntimeError):
    """Fail-closed chat-human interlock construction error."""


def _load(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChatHumanInterlockError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ChatHumanInterlockError(f"{label} must contain one JSON object")
    return value


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _result_ref(root: Path, evidence_commit: str, path: Path, review_id: str) -> dict[str, str]:
    source = path.resolve()
    try:
        rel = source.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ChatHumanInterlockError("review evidence path escapes repository") from exc
    raw = source.read_bytes()
    committed = subprocess.run(
        ["git", "-C", str(root), "show", f"{evidence_commit}:{rel}"],
        check=False,
        capture_output=True,
    )
    if committed.returncode != 0 or committed.stdout != raw:
        raise ChatHumanInterlockError(f"review evidence bytes are not exact at {evidence_commit}: {rel}")
    digest = _sha256(raw)
    return {
        "kind": "RESULT",
        "ref": f"git:{evidence_commit}:{rel}#{review_id}",
        "content_hash": digest,
    }


def _run_ref(run_id: str, label: str, path: Path) -> dict[str, str]:
    digest = _sha256(path.read_bytes())
    return {
        "kind": "RUN",
        "ref": f"run:github:{run_id}-{label}#{digest}",
        "content_hash": digest,
    }


def _ready(review: Mapping[str, Any], role: str, verdict: str) -> bool:
    return (
        review.get("role") == role
        and review.get("verdict") == verdict
        and review.get("confidence") in {"HIGH", "MEDIUM"}
        and review.get("evidence_status") == "SUFFICIENT"
        and review.get("missing_evidence") in (None, [])
    )


def build_chat_human_interlock(
    root: Path,
    *,
    task_id: str,
    accepted_task_commit: str,
    control_plane_commit: str,
    decision_id: str,
    q4_review_path: Path,
    q6_review_path: Path,
    evidence_commit: str,
    source_run_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    q4 = _load(q4_review_path, "Q4 review")
    q6 = _load(q6_review_path, "Q6 review")
    q4_packet_path = (root / str(q4.get("context_packet") or "")).resolve()
    q6_packet_path = (root / str(q6.get("context_packet") or "")).resolve()
    q4_packet = _load(q4_packet_path, "Q4 packet")
    q6_packet = _load(q6_packet_path, "Q6 packet")

    if current_task_commit(root, task_id) != accepted_task_commit:
        raise ChatHumanInterlockError("accepted task commit is not the current task snapshot")
    if q4.get("task") != task_id or q6.get("task") != task_id:
        raise ChatHumanInterlockError("Q4/Q6 task binding mismatch")
    if q4.get("review_id") != q4_packet.get("review_id"):
        raise ChatHumanInterlockError("Q4 packet/review identity mismatch")
    if q6.get("review_id") != q6_packet.get("review_id"):
        raise ChatHumanInterlockError("Q6 packet/review identity mismatch")
    if not _ready(q4, Q4_ROLE, "REVISE"):
        raise ChatHumanInterlockError("chat-human interlock requires one sufficient Q4 REVISE")
    if not _ready(q6, Q6_ROLE, "PASS"):
        raise ChatHumanInterlockError("chat-human interlock requires one sufficient Q6 PASS")

    recorded_scope = str(q6.get("review_scope_hash") or "")
    packet_scope = str(q6_packet.get("review_scope_hash") or "")
    current_scope = review_scope_hash(root, task_id, Q6_ROLE)
    if not recorded_scope or recorded_scope != packet_scope or recorded_scope != current_scope:
        raise ChatHumanInterlockError("Q6 production review_scope_hash is not current")

    validate_chat_human_risk_acceptance(
        root,
        envelope={"type": SATISFACTION_MODE, "decision_id": decision_id},
        q4_result=q4,
    )

    policy = RetrievalPolicy(root)
    authority = ExecutionAuthority(policy)
    role = authority.primary_role_for_stage(QUALITY_INTERLOCK)
    context = InvocationContext(
        stage_id=QUALITY_INTERLOCK,
        role_id=role,
        task_id=task_id,
        task_commit=accepted_task_commit,
        control_plane_commit=control_plane_commit,
    )
    invocation = StageInvocationBuilder(root, policy).build(
        context,
        {
            "FROZEN_TASK_COMMIT": accepted_task_commit,
            "Q4_CONTEXT_PACKET": q4_packet,
            "Q6_CONTEXT_PACKET": q6_packet,
            "Q6_REVIEW_SCOPE_HASH": recorded_scope,
        },
    )
    if invocation.get("readiness") != "READY":
        raise ChatHumanInterlockError(
            f"QUALITY_INTERLOCK invocation is not READY: {invocation.get('readiness')}"
        )

    outputs = {
        "Q4_RESULT": q4,
        "Q4_SATISFACTION": SATISFACTION_MODE,
        "Q4_CLOSURE_RESULT": {"type": SATISFACTION_MODE, "decision_id": decision_id},
        "Q6_RESULT": q6,
        "EVIDENCE_SUFFICIENCY": "SUFFICIENT",
    }
    result = {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": accepted_task_commit,
        "status": "QUALITY_INTERLOCK_PASS",
        "outputs": outputs,
        "evidence_refs": [
            {"kind": "COMMIT", "ref": f"commit:{accepted_task_commit}"},
            _result_ref(root, evidence_commit, q4_review_path, str(q4["review_id"])),
            _result_ref(root, evidence_commit, q6_review_path, str(q6["review_id"])),
            _run_ref(source_run_id, "q4", q4_review_path),
            _run_ref(source_run_id, "q6", q6_review_path),
        ],
    }
    return invocation, result


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-commit", required=True)
    parser.add_argument("--control-plane-commit", required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--q4-review", required=True)
    parser.add_argument("--q6-review", required=True)
    parser.add_argument("--evidence-commit", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--invocation-output", required=True)
    parser.add_argument("--result-output", required=True)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    invocation, result = build_chat_human_interlock(
        root,
        task_id=args.task_id,
        accepted_task_commit=args.task_commit,
        control_plane_commit=args.control_plane_commit,
        decision_id=args.decision_id,
        q4_review_path=(root / args.q4_review).resolve(),
        q6_review_path=(root / args.q6_review).resolve(),
        evidence_commit=args.evidence_commit,
        source_run_id=args.source_run_id,
    )
    _write(Path(args.invocation_output), invocation)
    _write(Path(args.result_output), result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
