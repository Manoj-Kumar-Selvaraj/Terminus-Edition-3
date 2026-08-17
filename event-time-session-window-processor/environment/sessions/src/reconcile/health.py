from __future__ import annotations

from pathlib import Path
from typing import Any

from src.runtime.journal_codec import (
    iter_journal_records,
    journal_seq_contiguous,
    journal_watermarks_nondecreasing,
)
from src.sinks.jsonl import read_jsonl
from src.reconcile.records import (
    closed_record_ok,
    late_record_ok,
    overlapping_closed,
    reject_record_ok,
)


def inspect_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    return read_jsonl(path)


def output_health(sessions_path: Path, late_path: Path, rejects_path: Path) -> dict[str, Any]:
    sessions = inspect_jsonl(sessions_path)
    late = inspect_jsonl(late_path)
    rejects = inspect_jsonl(rejects_path)
    closed_problems = [closed_record_ok(row) for row in sessions]
    late_problems = [late_record_ok(row) for row in late]
    reject_problems = [reject_record_ok(row) for row in rejects]
    return {
        "closed_count": len(sessions),
        "late_count": len(late),
        "reject_count": len(rejects),
        "closed_invalid": sum(1 for ok, _ in closed_problems if not ok),
        "late_invalid": sum(1 for ok, _ in late_problems if not ok),
        "reject_invalid": sum(1 for ok, _ in reject_problems if not ok),
        "overlapping_keys": [
            {"tenant_id": t, "user_id": u} for t, u in overlapping_closed(sessions)
        ],
    }


def journal_health(text: str) -> dict[str, Any]:
    recs = list(iter_journal_records(text))
    return {
        "entries": len(recs),
        "seq_contiguous": journal_seq_contiguous(text),
        "watermark_nondecreasing": journal_watermarks_nondecreasing(text),
        "last_seq": recs[-1]["seq"] if recs else None,
        "last_watermark_ms": recs[-1]["watermark_ms"] if recs else None,
        "last_max_observed": recs[-1]["max_observed_event_time_ms"] if recs else None,
    }
