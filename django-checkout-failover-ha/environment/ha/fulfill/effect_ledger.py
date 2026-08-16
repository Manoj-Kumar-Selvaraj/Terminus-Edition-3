"""Side-effect ledger queries used by dump_failover and readiness."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class EffectRow:
    attempt_id: str
    kind: str
    status: str
    write_lsn: int


def repeat_capture_count(rows: Sequence[EffectRow], *, kind: str = "capture") -> int:
    counter: Counter[str] = Counter()
    for row in rows:
        if row.kind != kind:
            continue
        counter[row.attempt_id] += 1
    return sum(n - 1 for n in counter.values() if n > 1)


def attempts_with_repeats(rows: Sequence[EffectRow], *, kind: str = "capture") -> list[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        if row.kind != kind:
            continue
        counter[row.attempt_id] += 1
    return sorted(attempt for attempt, n in counter.items() if n > 1)


def uncommitted_effects(
    rows: Sequence[EffectRow], *, committed_lsn: int
) -> list[EffectRow]:
    return [row for row in rows if int(row.write_lsn) > int(committed_lsn)]


def filter_kind(rows: Iterable[EffectRow], kind: str) -> list[EffectRow]:
    return [row for row in rows if row.kind == kind]


def status_histogram(rows: Sequence[EffectRow]) -> dict[str, int]:
    counter: Counter[str] = Counter(row.status for row in rows)
    return dict(sorted(counter.items()))
