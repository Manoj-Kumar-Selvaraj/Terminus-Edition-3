"""Append-only journal. event_id is stored without a payload fence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from yard.timeutil import format_instant, parse_instant


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            events.append(json.loads(text))
    events.sort(key=lambda item: int(item.get("seq", 0)))
    return events


def journal_head_seq(path: Path) -> int:
    events = read_events(path)
    if not events:
        return 0
    return int(events[-1]["seq"])


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":"), sort_keys=False))
        handle.write("\n")


def payload_view(event: dict[str, Any]) -> dict[str, Any]:
    skip = {"seq", "accepted_at"}
    return {key: event[key] for key in event if key not in skip}


def find_event(path: Path, event_id: str) -> Optional[dict[str, Any]]:
    for event in read_events(path):
        if event.get("event_id") == event_id:
            return event
    return None


def next_seq(path: Path) -> int:
    return journal_head_seq(path) + 1


def stamp(event: dict[str, Any], seq: int, accepted_at: str) -> dict[str, Any]:
    body = dict(event)
    body["seq"] = seq
    body["accepted_at"] = accepted_at
    return body


def parse_event_time(event: dict[str, Any]) -> str:
    for key in ("at", "accepted_at", "gate_in"):
        if event.get(key):
            return format_instant(parse_instant(str(event[key])))
    return event.get("accepted_at", "")
