from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.errors import reject_record
from src.ingest.lineio import is_blank_line
from src.ingest.scan import iter_nonempty, scan_source
from src.ingest.normalize import strip_unknown_nulls
from src.ingest.schema_event import first_type_error, missing_required_fields
from src.records import Event
from src.validation.fields import as_event_time, as_nonempty_str, as_payload, event_id_from_obj


def decode_line(line: str, line_no: int) -> tuple[Event | None, dict[str, Any] | None]:
    text = line.strip()
    if not text:
        return None, None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None, reject_record(None, "invalid json", line_no)
    if not isinstance(obj, dict):
        return None, reject_record(None, "not an object", line_no)
    obj = strip_unknown_nulls(obj)
    event_id = event_id_from_obj(obj)
    missing = missing_required_fields(obj)
    if missing:
        return None, reject_record(event_id, f"missing {missing[0]}", line_no)
    type_err = first_type_error(obj)
    if type_err is not None:
        return None, reject_record(event_id, type_err, line_no)
    try:
        event_id_s = as_nonempty_str(obj["event_id"], "event_id")
        tenant_id = as_nonempty_str(obj["tenant_id"], "tenant_id")
        user_id = as_nonempty_str(obj["user_id"], "user_id")
        event_time_ms = as_event_time(obj["event_time_ms"])
        payload = as_payload(obj["payload"])
    except (TypeError, ValueError) as exc:
        return None, reject_record(event_id, str(exc), line_no)
    return Event(event_id_s, tenant_id, user_id, event_time_ms, payload, line_no), None


def read_events(path: Path) -> tuple[list[Event], list[dict[str, Any]]]:
    events: list[Event] = []
    rejects: list[dict[str, Any]] = []
    if not path.is_file():
        return events, rejects
    scan = scan_source(path)
    if scan.decode_errors and scan.lines_seen == 0:
        return events, rejects
    for rec in iter_nonempty(scan):
        if is_blank_line(rec.text):
            continue
        ev, rej = decode_line(rec.text, rec.line_no)
        if rej is not None:
            rejects.append(rej)
        elif ev is not None:
            events.append(ev)
    return events, rejects
