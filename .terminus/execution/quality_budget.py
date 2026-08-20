#!/usr/bin/env python3
"""Persist and enforce per-task Terminus Q execution budgets.

Budget claims are immutable receipts stored on a dedicated state branch by CI.
Q4 may execute at most three times per task, Q6 at most twice, and every other
registered Q role/perspective at most once per task. A claim is made immediately
before a model-backed execution and therefore survives fresh runners and task
branches.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from execution.quality_execution_guard import ensure_review_output_unoccupied
    from execution.quality_executor import QualityExecutorError
else:
    from .quality_execution_guard import ensure_review_output_unoccupied
    from .quality_executor import QualityExecutorError

Q_ROLE_CODES = {
    "Spec Gap Repairer": "q1",
    "Verifier Coverage Repairer": "q2",
    "Spec Ambiguity Repairer": "q3",
    "Spec-Test Contract Reviewer": "q4",
    "Oracle & Runtime Repair Specialist": "q5",
    "Production Logic Auditor": "q6",
    "Task Format Enforcer": "q7",
    "Model Perspective Difficulty Simulator": "q8",
}
Q_ROLE_LIMITS = {role: 1 for role in Q_ROLE_CODES}
Q_ROLE_LIMITS["Spec-Test Contract Reviewer"] = 3
Q_ROLE_LIMITS["Production Logic Auditor"] = 2
STATE_DIR = "q-runs"
Q8_ROLE = "Model Perspective Difficulty Simulator"


class QualityBudgetError(RuntimeError):
    """Fail-closed Q-budget error."""


def execution_limit(role: str) -> int:
    return Q_ROLE_LIMITS.get(role, 1)


def role_code(role: str) -> str:
    if role in Q_ROLE_CODES:
        return Q_ROLE_CODES[role]
    slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-")
    return slug or "q-unknown"


def budget_code(packet: Mapping[str, Any]) -> str:
    """Return the immutable per-task budget bucket for one packet.

    Q8 has two mandatory isolated perspectives. Each perspective is a distinct
    one-shot budget bucket so the required GPT and Claude runs do not consume
    each other's single allowed execution.
    """

    role = str(packet.get("role") or "")
    code = role_code(role)
    if role != Q8_ROLE:
        return code

    review_id = str(packet.get("review_id") or "").lower()
    question = str(packet.get("question") or "").lower()
    if "difficulty-sim-gpt" in review_id or "gpt/codex-style" in question:
        return "q8-gpt"
    if "difficulty-sim-claude" in review_id or "claude/claude-code-style" in question:
        return "q8-claude"
    raise QualityBudgetError("Q8 packet must identify exactly one GPT or Claude perspective")


def _safe_task(value: Any) -> str:
    task = str(value or "")
    if not task or task.startswith(".") or "/" in task or "\\" in task or ".." in task:
        raise QualityBudgetError("packet task must be one safe top-level directory")
    return task


def _safe_run_number(value: str, label: str) -> str:
    rendered = str(value).strip()
    if not re.fullmatch(r"[0-9]+", rendered):
        raise QualityBudgetError(f"{label} must be numeric")
    return rendered


def load_packet(path: Path) -> dict[str, Any]:
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityBudgetError(f"cannot read packet: {exc}") from exc
    if not isinstance(packet, dict):
        raise QualityBudgetError("packet must contain one JSON object")
    for field in (
        "task",
        "task_commit",
        "control_plane_commit",
        "review_id",
        "role",
        "review_output_path",
    ):
        if not packet.get(field):
            raise QualityBudgetError(f"packet missing {field}")
    return packet


def _existing_receipts(
    role_dir: Path, task: str, role: str, q_stage: str
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    if not role_dir.exists():
        return receipts
    for path in sorted(role_dir.glob("*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise QualityBudgetError(f"malformed budget receipt {path}: {exc}") from exc
        if not isinstance(receipt, dict):
            raise QualityBudgetError(f"budget receipt is not an object: {path}")
        if receipt.get("task") != task or receipt.get("role") != role:
            raise QualityBudgetError(f"budget receipt identity drift: {path}")
        if str(receipt.get("q_stage") or "").lower() != q_stage:
            raise QualityBudgetError(f"budget receipt stage drift: {path}")
        receipts.append(receipt)
    return receipts


def claim_quality_budget(
    state_root: Path,
    packet: Mapping[str, Any],
    *,
    packet_path: str,
    backend: str,
    run_id: str,
    run_attempt: str,
) -> dict[str, Any]:
    """Create one idempotent immutable claim, or fail when the task limit is exhausted."""

    task = _safe_task(packet.get("task"))
    role = str(packet.get("role") or "")
    if not role:
        raise QualityBudgetError("packet missing role")
    code = budget_code(packet)
    limit = execution_limit(role)
    run_id = _safe_run_number(run_id, "run_id")
    run_attempt = _safe_run_number(run_attempt, "run_attempt")
    state_root = state_root.resolve()
    role_dir = state_root / STATE_DIR / task / code
    role_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = role_dir / f"{run_id}-{run_attempt}.json"

    existing = _existing_receipts(role_dir, task, role, code)
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("backend") != backend or receipt.get("packet") != packet_path:
            raise QualityBudgetError("existing run-attempt receipt has different execution identity")
        return {
            "status": "ALREADY_CLAIMED",
            "task": task,
            "role": role,
            "q_stage": code.upper(),
            "used": len(existing),
            "limit": limit,
            "remaining": max(0, limit - len(existing)),
            "receipt": receipt_path.relative_to(state_root).as_posix(),
        }

    if len(existing) >= limit:
        raise QualityBudgetError(
            f"{code.upper()} execution budget exhausted for task {task}: {len(existing)}/{limit}"
        )

    ordinal = len(existing) + 1
    receipt = {
        "schema_version": "1.0",
        "task": task,
        "role": role,
        "q_stage": code.upper(),
        "ordinal": ordinal,
        "limit": limit,
        "packet": packet_path,
        "review_id": str(packet.get("review_id")),
        "task_commit": str(packet.get("task_commit")),
        "control_plane_commit": str(packet.get("control_plane_commit")),
        "backend": backend,
        "github_run_id": run_id,
        "github_run_attempt": run_attempt,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "CLAIMED",
        "task": task,
        "role": role,
        "q_stage": code.upper(),
        "used": ordinal,
        "limit": limit,
        "remaining": limit - ordinal,
        "receipt": receipt_path.relative_to(state_root).as_posix(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--packet", required=True)
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        packet = load_packet(Path(args.packet))
        ensure_review_output_unoccupied(Path(args.root), packet)
        result = claim_quality_budget(
            Path(args.state_root),
            packet,
            packet_path=str(args.packet),
            backend=args.backend,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
        )
    except (QualityBudgetError, QualityExecutorError) as exc:
        print(f"quality budget failed: {exc}")
        return 2

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
