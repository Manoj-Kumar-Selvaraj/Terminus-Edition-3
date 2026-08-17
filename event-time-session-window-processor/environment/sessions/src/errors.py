from __future__ import annotations

from typing import Any

REJECT_MALFORMED = "REJECT_MALFORMED"
TOO_LATE = "TOO_LATE"


def reject_record(event_id: str | None, detail: str, line_no: int) -> dict[str, Any]:
    return {
        "code": REJECT_MALFORMED,
        "event_id": event_id,
        "detail": str(detail)[:240],
        "line_no": int(line_no),
    }


def late_record(
    event_id: str,
    tenant_id: str,
    user_id: str,
    event_time_ms: int,
    watermark_ms: int,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "event_time_ms": int(event_time_ms),
        "watermark_ms": int(watermark_ms),
        "reason": TOO_LATE,
    }


def closed_session_record(
    tenant_id: str,
    user_id: str,
    start_ms: int,
    end_ms: int,
    event_ids: list[str],
) -> dict[str, Any]:
    ids = list(event_ids)
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "start_ms": int(start_ms),
        "end_ms": int(end_ms),
        "event_ids": ids,
        "event_count": len(ids),
    }
