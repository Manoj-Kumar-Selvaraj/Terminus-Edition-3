from __future__ import annotations

import json
from typing import Any, Iterator

JOURNAL_FIELDS = ("watermark_ms", "max_observed_event_time_ms", "seq")


def encode_journal_record(watermark_ms: int, max_observed: int, seq: int) -> str:
    rec = {
        "watermark_ms": int(watermark_ms),
        "max_observed_event_time_ms": int(max_observed),
        "seq": int(seq),
    }
    return json.dumps(rec, separators=(",", ":"), sort_keys=True)


def _as_int_field(obj: dict[str, Any], field: str) -> int:
    value = obj[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(field)
    return int(value)


def decode_journal_record(line: str) -> dict[str, Any] | None:
    text = line.strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    if any(field not in obj for field in JOURNAL_FIELDS):
        return None
    try:
        return {
            "watermark_ms": _as_int_field(obj, "watermark_ms"),
            "max_observed_event_time_ms": _as_int_field(obj, "max_observed_event_time_ms"),
            "seq": _as_int_field(obj, "seq"),
        }
    except (TypeError, KeyError, ValueError):
        return None


def iter_journal_records(text: str) -> Iterator[dict[str, Any]]:
    for line in text.splitlines():
        rec = decode_journal_record(line)
        if rec is not None:
            yield rec


def last_journal_values(text: str) -> tuple[int, int, int] | None:
    last = None
    for rec in iter_journal_records(text):
        last = rec
    if last is None:
        return None
    return last["seq"], last["watermark_ms"], last["max_observed_event_time_ms"]


def journal_seq_contiguous(text: str) -> bool:
    seqs = [rec["seq"] for rec in iter_journal_records(text)]
    if not seqs:
        return True
    return seqs == list(range(1, len(seqs) + 1))


def journal_watermarks_nondecreasing(text: str) -> bool:
    prev = None
    for rec in iter_journal_records(text):
        wm = rec["watermark_ms"]
        if prev is not None and wm < prev:
            return False
        prev = wm
    return True


def journal_max_observed_nondecreasing(text: str) -> bool:
    prev = None
    for rec in iter_journal_records(text):
        observed = rec["max_observed_event_time_ms"]
        if prev is not None and observed < prev:
            return False
        prev = observed
    return True


def journal_formula_holds(text: str, allowed_lateness_ms: int) -> bool:
    for rec in iter_journal_records(text):
        expected = rec["max_observed_event_time_ms"] - int(allowed_lateness_ms)
        if rec["watermark_ms"] != expected:
            return False
    return True


def journal_health_report(text: str, allowed_lateness_ms: int | None = None) -> dict[str, bool | int]:
    records = list(iter_journal_records(text))
    report: dict[str, bool | int] = {
        "lines": len(records),
        "contiguous_seq": journal_seq_contiguous(text),
        "watermark_nondecreasing": journal_watermarks_nondecreasing(text),
        "max_observed_nondecreasing": journal_max_observed_nondecreasing(text),
    }
    if allowed_lateness_ms is not None:
        report["formula_ok"] = journal_formula_holds(text, allowed_lateness_ms)
    return report
