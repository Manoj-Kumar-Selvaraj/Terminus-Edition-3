"""Count and list helpers for snapshot counts."""

from __future__ import annotations

from typing import Any, Iterable


def count_occupied(occupancy: Iterable[dict[str, Any]]) -> int:
    return sum(1 for row in occupancy if row.get("visit_id"))


def count_doors(doors: Iterable[dict[str, Any]]) -> int:
    return sum(1 for row in doors if row.get("visit_id"))


def count_holds(holds: Iterable[dict[str, Any]]) -> int:
    return sum(1 for _ in holds)


def count_transit(rows: Iterable[dict[str, Any]]) -> int:
    return sum(1 for _ in rows)


def build_counts(
    open_visits: list[dict[str, Any]],
    occupancy: list[dict[str, Any]],
    doors: list[dict[str, Any]],
    transit: list[dict[str, Any]],
    holds: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "open_visits": len(open_visits),
        "occupied_spots": count_occupied(occupancy),
        "doors_occupied": count_doors(doors),
        "in_transit": count_transit(transit),
        "active_holds": count_holds(holds),
    }
