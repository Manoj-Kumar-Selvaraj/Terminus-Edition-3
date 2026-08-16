from __future__ import annotations

from typing import Any

from cc.audit.log import all_events


def by_principal(principal: str) -> list[dict[str, Any]]:
    return [e for e in all_events() if e.get("principal") == principal]


def denied_only() -> list[dict[str, Any]]:
    return [e for e in all_events() if not e.get("allowed")]


def for_repo(repo: str) -> list[dict[str, Any]]:
    needle = f":{repo}"
    return [e for e in all_events() if needle in str(e.get("resource", ""))]


def summary() -> dict[str, Any]:
    rows = all_events()
    return {
        "total": len(rows),
        "allowed": sum(1 for r in rows if r.get("allowed")),
        "denied": sum(1 for r in rows if not r.get("allowed")),
        "principals": sorted({str(r.get("principal")) for r in rows}),
    }
