"""Durable task-time telemetry with non-blocking advisory guidance.

Time accounting is intentionally orthogonal to lifecycle authority. It may help
an orchestrator understand where time is being spent, but elapsed time never
changes gate state, blocks a stage, requests an extension, or weakens quality.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
DEFAULT_GUIDANCE_SECONDS = 7 * 60 * 60
# Compatibility alias for callers that previously consumed the target field.
DEFAULT_TARGET_SECONDS = DEFAULT_GUIDANCE_SECONDS
DEFAULT_HARD_SECONDS: int | None = None
DEFAULT_EXTENSION_MINUTES = 60
MIN_EXTENSION_MINUTES = 5
MAX_EXTENSION_MINUTES = 8 * 60
TIME_CATEGORIES = frozenset(
    {
        "PLANNED_EXECUTION",
        "QUALITY_REVIEW",
        "DETERMINISTIC_VALIDATION",
        "SEMANTIC_REPAIR",
        "REVIEWER_REWORK",
        "INFRA_FAILURE",
        "AGENT_TOOL_FAILURE",
        "UPLOAD_FAILURE",
        "POLICY_DISAGREEMENT",
        "UNNECESSARY_LOOP",
        "OTHER",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty ISO-8601 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_id(prefix: str, value: Mapping[str, Any]) -> str:
    return prefix + "_" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BudgetPolicy:
    """Advisory task-duration guidance.

    ``hard_seconds`` is retained only as a compatibility input for older callers.
    It is never enforced and is not projected as a lifecycle limit.
    """

    target_seconds: int = DEFAULT_GUIDANCE_SECONDS
    hard_seconds: int | None = DEFAULT_HARD_SECONDS

    def __post_init__(self) -> None:
        if self.target_seconds <= 0:
            raise ValueError("target_seconds must be positive")
        if self.hard_seconds is not None and self.hard_seconds <= 0:
            raise ValueError("hard_seconds must be positive when supplied")


class TaskTimeBudget:
    """Append-only timing telemetry plus advisory task-duration projection."""

    schema_version = "1.1"

    def __init__(
        self,
        root: Path,
        task_id: str,
        *,
        policy: BudgetPolicy | None = None,
    ):
        self.root = root.resolve()
        if not isinstance(task_id, str) or not _TASK_ID.fullmatch(task_id):
            raise ValueError("task_id must be a safe repository-local identifier")
        self.task_id = task_id
        self.policy = policy or BudgetPolicy()
        self.directory = (
            self.root / ".terminus" / "executions" / task_id / "time_budget"
        )
        self.events_path = self.directory / "events.jsonl"
        self.extensions_path = self.directory / "extensions.jsonl"

    def begin(
        self,
        stage_id: str,
        *,
        source: str = "MANUAL_CHAT",
        started_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Optionally start a telemetry span; this never grants routing authority."""
        if not isinstance(stage_id, str) or not stage_id.strip():
            raise ValueError("stage_id must be non-empty")
        if self.active_span() is not None:
            raise ValueError("a task-time span is already active")
        stamp = _iso(started_at or _utcnow())
        payload = {
            "schema_version": self.schema_version,
            "kind": "START",
            "task_id": self.task_id,
            "stage_id": stage_id.strip(),
            "source": str(source or "UNKNOWN"),
            "started_at": stamp,
        }
        payload["span_id"] = _stable_id("span", payload)
        self._append(self.events_path, payload)
        return payload

    def finish(
        self,
        *,
        paused_seconds: int = 0,
        category: str = "PLANNED_EXECUTION",
        finished_at: datetime | None = None,
    ) -> dict[str, Any]:
        if paused_seconds < 0:
            raise ValueError("paused_seconds must be non-negative")
        category = self._category(category)
        active = self.active_span()
        if active is None:
            raise ValueError("no active task-time span exists")
        finished = finished_at or _utcnow()
        started = _parse_iso(str(active["started_at"]))
        wall = max(0, int(round((finished - started).total_seconds())))
        counted = max(0, wall - int(paused_seconds))
        payload = {
            "schema_version": self.schema_version,
            "kind": "FINISH",
            "task_id": self.task_id,
            "span_id": active["span_id"],
            "stage_id": active["stage_id"],
            "source": active["source"],
            "started_at": active["started_at"],
            "finished_at": _iso(finished),
            "wall_seconds": wall,
            "paused_seconds": int(paused_seconds),
            "counted_seconds": counted,
            "category": category,
        }
        payload["event_id"] = _stable_id("time", payload)
        self._append(self.events_path, payload)
        return payload

    def record_run(
        self,
        stage_id: str,
        counted_seconds: int,
        *,
        category: str = "DETERMINISTIC_VALIDATION",
        source: str = "EXTERNAL_RUN",
        finished_at: datetime | None = None,
        run_ref: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(stage_id, str) or not stage_id.strip():
            raise ValueError("stage_id must be non-empty")
        if counted_seconds < 0:
            raise ValueError("counted_seconds must be non-negative")
        category = self._category(category)
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "kind": "RUN",
            "task_id": self.task_id,
            "stage_id": stage_id.strip(),
            "source": str(source or "EXTERNAL_RUN"),
            "finished_at": _iso(finished_at or _utcnow()),
            "counted_seconds": int(counted_seconds),
            "category": category,
        }
        if run_ref:
            payload["run_ref"] = str(run_ref)
        payload["event_id"] = _stable_id("time", payload)
        self._append(self.events_path, payload)
        return payload

    def grant_extension(
        self,
        minutes: int,
        *,
        approved_by: str,
        reason: str = "",
        approved_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Record legacy advisory metadata without changing lifecycle routing.

        Extensions are retained for backward compatibility with existing ledgers.
        The seven-hour guidance remains advisory and does not require extension.
        """
        if minutes < MIN_EXTENSION_MINUTES or minutes > MAX_EXTENSION_MINUTES:
            raise ValueError(
                f"extension minutes must be between {MIN_EXTENSION_MINUTES} "
                f"and {MAX_EXTENSION_MINUTES}"
            )
        if not isinstance(approved_by, str) or not approved_by.strip():
            raise ValueError("approved_by must identify the human approver")
        payload = {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "minutes": int(minutes),
            "seconds": int(minutes) * 60,
            "approved_by": approved_by.strip(),
            "reason": str(reason).strip(),
            "approved_at": _iso(approved_at or _utcnow()),
            "advisory_only": True,
        }
        payload["extension_id"] = _stable_id("extension", payload)
        self._append(self.extensions_path, payload)
        return payload

    def active_span(self) -> dict[str, Any] | None:
        starts: dict[str, dict[str, Any]] = {}
        finished: set[str] = set()
        for row in self._read(self.events_path):
            kind = row.get("kind")
            if kind == "START":
                starts[str(row["span_id"])] = row
            elif kind == "FINISH":
                finished.add(str(row["span_id"]))
        active = [row for span_id, row in starts.items() if span_id not in finished]
        if len(active) > 1:
            raise ValueError("time budget ledger contains overlapping active spans")
        return active[0] if active else None

    def snapshot(
        self,
        *,
        remaining_mandatory_stages: int | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if remaining_mandatory_stages is not None and remaining_mandatory_stages < 0:
            raise ValueError("remaining_mandatory_stages must be non-negative")
        totals: dict[str, int] = defaultdict(int)
        categories: dict[str, int] = defaultdict(int)
        completed_spans = 0
        run_events = 0
        consumed = 0
        for row in self._read(self.events_path):
            if row.get("kind") not in {"FINISH", "RUN"}:
                continue
            seconds = int(row.get("counted_seconds", 0))
            if seconds < 0:
                raise ValueError("time budget ledger contains negative counted_seconds")
            consumed += seconds
            totals[str(row.get("stage_id", "UNKNOWN"))] += seconds
            categories[str(row.get("category", "OTHER"))] += seconds
            if row.get("kind") == "FINISH":
                completed_spans += 1
            else:
                run_events += 1

        extensions = self._read(self.extensions_path)
        legacy_extension_seconds = sum(int(row.get("seconds", 0)) for row in extensions)
        guidance = self.policy.target_seconds
        remaining = max(0, guidance - consumed)
        burn_ratio = consumed / guidance if guidance else 0.0
        guidance_exceeded = consumed > guidance

        active = self.active_span()
        active_view: dict[str, Any] | None = None
        if active is not None:
            current = now or _utcnow()
            elapsed = max(
                0,
                int(
                    round(
                        (current - _parse_iso(str(active["started_at"]))).total_seconds()
                    )
                ),
            )
            active_view = dict(active)
            active_view["elapsed_wall_seconds"] = elapsed

        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "enforcement": "ADVISORY_ONLY",
            "guidance_seconds": guidance,
            "target_seconds": guidance,
            "hard_limit_seconds": None,
            "base_target_seconds": guidance,
            "base_hard_limit_seconds": None,
            "extension_seconds": legacy_extension_seconds,
            "consumed_seconds": consumed,
            "target_remaining_seconds": remaining,
            "hard_remaining_seconds": None,
            "burn_ratio": round(burn_ratio, 4),
            "mode": "ADVISORY_OVER_GUIDANCE" if guidance_exceeded else "ADVISORY",
            "guidance_exceeded": guidance_exceeded,
            "remaining_mandatory_stages": remaining_mandatory_stages,
            "recommended_next_stage_seconds": None,
            "request_time_extension": False,
            "suggested_extension_minutes": None,
            "stage_totals_seconds": dict(sorted(totals.items())),
            "category_totals_seconds": dict(sorted(categories.items())),
            "completed_stage_spans": completed_spans,
            "recorded_run_events": run_events,
            "extensions": len(extensions),
            "active_span": active_view,
        }

    def project_workflow(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        """Attach telemetry without ever changing the controller's next action."""
        projected = json.loads(json.dumps(snapshot))
        nodes = projected.get("nodes", [])
        remaining = sum(
            1
            for node in nodes
            if isinstance(node, dict)
            and node.get("node_kind") == "STAGE"
            and node.get("status") != "CURRENT"
        )
        projected["time_budget"] = self.snapshot(remaining_mandatory_stages=remaining)
        return projected

    def _category(self, value: str) -> str:
        normalized = str(value).strip().upper()
        if normalized not in TIME_CATEGORIES:
            raise ValueError(
                "unknown time category; expected one of "
                + ", ".join(sorted(TIME_CATEGORIES))
            )
        return normalized

    @staticmethod
    def _read(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line_number, raw in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"time ledger row {line_number} is not an object")
            rows.append(value)
        return rows

    @staticmethod
    def _append(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = _canonical(payload) + "\n"
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
