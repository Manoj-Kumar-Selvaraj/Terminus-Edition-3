"""Inventory reservation ledger semantics for checkout attempts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class ReservationState(str, Enum):
    HELD = "held"
    COMMITTED = "committed"
    RELEASED = "released"
    MISSING = "missing"


@dataclass
class ReservationLine:
    warehouse_id: int
    product_id: int
    qty: int
    attempt_id: str
    state: ReservationState = ReservationState.HELD


@dataclass
class ReservationLedger:
    lines: list[ReservationLine] = field(default_factory=list)

    def hold(self, line: ReservationLine) -> ReservationLine:
        existing = self.find(line.attempt_id, line.product_id)
        if existing is not None:
            return existing
        self.lines.append(line)
        return line

    def find(self, attempt_id: str, product_id: int) -> ReservationLine | None:
        for line in self.lines:
            if line.attempt_id == attempt_id and line.product_id == product_id:
                return line
        return None

    def commit_attempt(self, attempt_id: str) -> list[ReservationLine]:
        changed: list[ReservationLine] = []
        for line in self.lines:
            if line.attempt_id != attempt_id:
                continue
            if line.state == ReservationState.HELD:
                line.state = ReservationState.COMMITTED
                changed.append(line)
        return changed

    def release_attempt(self, attempt_id: str) -> list[ReservationLine]:
        changed: list[ReservationLine] = []
        for line in self.lines:
            if line.attempt_id != attempt_id:
                continue
            if line.state == ReservationState.HELD:
                line.state = ReservationState.RELEASED
                changed.append(line)
        return changed

    def committed(self, attempt_id: str) -> bool:
        rows = [line for line in self.lines if line.attempt_id == attempt_id]
        if not rows:
            return False
        return all(line.state == ReservationState.COMMITTED for line in rows)


def stock_delta_for_commit(lines: Iterable[ReservationLine]) -> dict[tuple[int, int], int]:
    deltas: dict[tuple[int, int], int] = {}
    for line in lines:
        if line.state != ReservationState.COMMITTED:
            continue
        key = (int(line.warehouse_id), int(line.product_id))
        deltas[key] = deltas.get(key, 0) - int(line.qty)
    return deltas


def detect_double_commit(events: list[str]) -> int:
    """Count how many attempt_ids appear more than once in commit event stream."""
    counts: dict[str, int] = {}
    for attempt_id in events:
        counts[attempt_id] = counts.get(attempt_id, 0) + 1
    return sum(1 for n in counts.values() if n > 1)
