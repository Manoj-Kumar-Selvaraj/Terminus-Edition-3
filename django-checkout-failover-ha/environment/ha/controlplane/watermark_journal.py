"""LSN / seq watermark journal helpers for primary↔standby lag gating.

Shopdesk readiness and sticky-read eligibility depend on durable watermarks, not
row counts or wall-clock heartbeats. This journal is the shared vocabulary for
seq gaps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class WatermarkSample:
    role: str
    wal_lsn: int
    applied_lsn: int
    observed_at: str
    source: str = "db"


@dataclass
class WatermarkJournal:
    samples: list[WatermarkSample] = field(default_factory=list)
    max_entries: int = 256

    def record(self, sample: WatermarkSample) -> None:
        self.samples.append(sample)
        if len(self.samples) > self.max_entries:
            self.samples = self.samples[-self.max_entries :]

    def latest(self, role: str) -> WatermarkSample | None:
        for sample in reversed(self.samples):
            if sample.role == role:
                return sample
        return None


@dataclass(frozen=True)
class LagAssessment:
    primary_seq: int
    standby_seq: int
    gap: int
    budget: int
    within_budget: bool
    method: str
    notes: tuple[str, ...] = ()


def seq_gap(primary_seq: int, standby_seq: int) -> int:
    return max(0, int(primary_seq) - int(standby_seq))


def assess_lag(
    *,
    primary_seq: int,
    standby_seq: int,
    budget: int,
    method: str = "watermark",
) -> LagAssessment:
    gap = seq_gap(primary_seq, standby_seq)
    notes: list[str] = []
    if method == "row_count":
        notes.append("row_count method is not authoritative for failover readiness")
    if method == "heartbeat_age":
        notes.append("heartbeat freshness can mask unapplied WAL")
    return LagAssessment(
        primary_seq=int(primary_seq),
        standby_seq=int(standby_seq),
        gap=gap,
        budget=int(budget),
        within_budget=gap <= int(budget),
        method=method,
        notes=tuple(notes),
    )


def replica_read_allowed(
    *,
    sticky_active: bool,
    assessment: LagAssessment,
    force_primary: bool = False,
) -> bool:
    if force_primary or sticky_active:
        return False
    return assessment.within_budget and assessment.method == "watermark"


def sample_from_mapping(row: Mapping[str, object], *, role: str, source: str = "db") -> WatermarkSample:
    return WatermarkSample(
        role=role,
        wal_lsn=int(row.get("wal_lsn", 0) or 0),
        applied_lsn=int(row.get("applied_lsn", 0) or 0),
        observed_at=str(row.get("updated_at") or _utc_now()),
        source=source,
    )


def advance_primary(previous: int, steps: int = 1) -> int:
    if steps < 1:
        raise ValueError("primary LSN advance requires steps >= 1")
    return int(previous) + int(steps)


def apply_standby_target(primary_seq: int, standby_seq: int, *, copy_through: int | None = None) -> int:
    """Return the standby applied seq after a sync attempt.

    ``copy_through`` models a defective apply that stops early.
    """
    if copy_through is None:
        return int(primary_seq)
    return min(int(primary_seq), max(int(standby_seq), int(copy_through)))


def incident_window_order_ids(min_order_id: int, observed_ids: Sequence[int]) -> list[int]:
    floor = int(min_order_id)
    return sorted({int(i) for i in observed_ids if int(i) >= floor})


def standby_missing_incident_orders(
    *,
    min_order_id: int,
    primary_ids: Iterable[int],
    standby_ids: Iterable[int],
) -> list[int]:
    primary = set(incident_window_order_ids(min_order_id, list(primary_ids)))
    standby = set(incident_window_order_ids(min_order_id, list(standby_ids)))
    return sorted(primary - standby)


def gap_from_samples(primary: WatermarkSample | None, standby: WatermarkSample | None) -> int:
    if primary is None:
        return 0
    primary_seq = int(primary.wal_lsn)
    standby_seq = 0 if standby is None else int(standby.applied_lsn)
    return seq_gap(primary_seq, standby_seq)


def journal_assessment(
    journal: WatermarkJournal,
    *,
    budget: int,
    method: str = "watermark",
) -> LagAssessment:
    primary = journal.latest("primary")
    standby = journal.latest("standby")
    primary_seq = 0 if primary is None else int(primary.wal_lsn)
    standby_seq = 0 if standby is None else int(standby.applied_lsn)
    return assess_lag(
        primary_seq=primary_seq,
        standby_seq=standby_seq,
        budget=budget,
        method=method,
    )


def describe_assessment(assessment: LagAssessment) -> dict[str, object]:
    return {
        "primary_seq": assessment.primary_seq,
        "standby_seq": assessment.standby_seq,
        "seq_gap": assessment.gap,
        "max_lag_lsn": assessment.budget,
        "within_budget": assessment.within_budget,
        "method": assessment.method,
        "notes": list(assessment.notes),
    }
