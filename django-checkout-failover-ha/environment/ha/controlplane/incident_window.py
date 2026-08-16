"""Incident-window order coverage checks for standby replay."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class IncidentWindow:
    min_order_id: int
    primary_refs: tuple[str, ...]
    standby_refs: tuple[str, ...]

    @property
    def missing_refs(self) -> tuple[str, ...]:
        have = set(self.standby_refs)
        return tuple(ref for ref in self.primary_refs if ref not in have)

    @property
    def covered(self) -> bool:
        return not self.missing_refs


def build_window(
    *,
    min_order_id: int,
    primary_pairs: Sequence[tuple[int, str]],
    standby_refs: Iterable[str],
) -> IncidentWindow:
    primary_refs = tuple(
        ref for order_id, ref in primary_pairs if int(order_id) >= int(min_order_id)
    )
    return IncidentWindow(
        min_order_id=int(min_order_id),
        primary_refs=primary_refs,
        standby_refs=tuple(standby_refs),
    )


def standby_only_refs(primary_refs: Iterable[str], standby_refs: Iterable[str]) -> list[str]:
    primary = set(primary_refs)
    return sorted(ref for ref in standby_refs if ref not in primary)


def summarize_window(window: IncidentWindow) -> dict[str, object]:
    return {
        "min_order_id": window.min_order_id,
        "primary_count": len(window.primary_refs),
        "standby_count": len(window.standby_refs),
        "missing_count": len(window.missing_refs),
        "covered": window.covered,
        "missing_sample": list(window.missing_refs[:5]),
    }
