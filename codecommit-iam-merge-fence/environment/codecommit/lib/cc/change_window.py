"""Change-window and freeze-calendar helpers for protected refs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cc import home
from cc.ref_guard import classify_ref
from cc.util import dump_json, full_ref, load_json

DEFAULT_WINDOWS = {
    "main": {"tz": "UTC", "allow_hours": list(range(12, 20)), "allow_weekdays": [0, 1, 2, 3]},
    "release": {"tz": "UTC", "allow_hours": list(range(14, 18)), "allow_weekdays": [1, 2]},
}


def load_calendar() -> dict[str, Any]:
    path = home.var_dir() / "change-calendar.json"
    return load_json(path, {"windows": DEFAULT_WINDOWS, "freezes": []})


def save_calendar(doc: dict[str, Any]) -> None:
    path = home.var_dir() / "change-calendar.json"
    dump_json(path, doc)


def upsert_freeze(name: str, start: str, end: str, refs: list[str]) -> dict[str, Any]:
    doc = load_calendar()
    freezes = list(doc.get("freezes") or [])
    entry = {"name": name, "start": start, "end": end, "refs": [full_ref(r) for r in refs]}
    freezes = [f for f in freezes if f.get("name") != name]
    freezes.append(entry)
    doc["freezes"] = freezes
    save_calendar(doc)
    return entry


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def active_freezes(now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    active: list[dict[str, Any]] = []
    for fr in load_calendar().get("freezes") or []:
        try:
            start = _parse(str(fr.get("start")))
            end = _parse(str(fr.get("end")))
        except Exception:  # noqa: BLE001
            continue
        if start <= now <= end:
            active.append(fr)
    return active


def ref_frozen(ref: str, now: datetime | None = None) -> bool:
    ref_n = full_ref(ref)
    for fr in active_freezes(now):
        targets = [full_ref(str(r)) for r in fr.get("refs") or []]
        if ref_n in targets or any(t.endswith("/*") and ref_n.startswith(t[:-1]) for t in targets):
            return True
    return False


def inside_window(ref: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    kind = str(classify_ref(ref).get("kind") or "feature")
    windows = load_calendar().get("windows") or DEFAULT_WINDOWS
    window = windows.get(kind) or windows.get("main") or DEFAULT_WINDOWS["main"]
    allowed = now.weekday() in set(window.get("allow_weekdays") or []) and now.hour in set(
        window.get("allow_hours") or []
    )
    return {
        "ref": full_ref(ref),
        "kind": kind,
        "allowed": allowed and not ref_frozen(ref, now),
        "frozen": ref_frozen(ref, now),
        "weekday": now.weekday(),
        "hour": now.hour,
        "window": window,
    }


def evaluate_refs(refs: list[str], now: datetime | None = None) -> list[dict[str, Any]]:
    return [inside_window(r, now) for r in refs]


def gate_message(ref: str, now: datetime | None = None) -> str | None:
    result = inside_window(ref, now)
    if result["frozen"]:
        return "CHANGE_FREEZE"
    if not result["allowed"]:
        return "OUTSIDE_CHANGE_WINDOW"
    return None
