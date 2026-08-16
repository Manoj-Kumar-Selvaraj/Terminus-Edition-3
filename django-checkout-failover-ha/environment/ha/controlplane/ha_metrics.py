"""Operational metrics and probe aggregations for Shopdesk HA.

These counters are derived from live desk state so /readyz and dump_failover can
share one vocabulary for writer count, lag, pins, and capture duplicates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


@dataclass
class HaMetrics:
    writer_count: int = 0
    writers: list[str] = field(default_factory=list)
    primary_seq: int = 0
    standby_seq: int = 0
    seq_gap: int = 0
    max_lag_lsn: int = 0
    pins_shared: bool = False
    pins_reachable: bool = False
    repeat_captures: int = 0
    standby_only_orders: int = 0
    fence_copied_to_standby: bool = False
    incident_orders_on_standby: bool = False
    process_up: bool = True

    def lag_ok(self) -> bool:
        return int(self.seq_gap) <= int(self.max_lag_lsn)

    def writer_ok(self) -> bool:
        return int(self.writer_count) == 1

    def pins_ok(self) -> bool:
        return bool(self.pins_shared and self.pins_reachable)

    def captures_ok(self) -> bool:
        return int(self.repeat_captures) == 0

    def standby_ok(self) -> bool:
        return (
            int(self.standby_only_orders) == 0
            and bool(self.incident_orders_on_standby)
            and not bool(self.fence_copied_to_standby)
        )

    def accepting(self) -> bool:
        return (
            self.process_up
            and self.writer_ok()
            and self.lag_ok()
            and self.pins_ok()
            and self.captures_ok()
            and self.standby_ok()
        )


def metrics_from_mapping(raw: Mapping[str, object]) -> HaMetrics:
    writers = [str(w) for w in list(raw.get("writers_seen") or [])]
    return HaMetrics(
        writer_count=len(writers),
        writers=writers,
        primary_seq=int(raw.get("primary_seq", 0) or 0),
        standby_seq=int(raw.get("standby_seq", 0) or 0),
        seq_gap=int(raw.get("seq_gap", 0) or 0),
        max_lag_lsn=int(raw.get("max_lag_lsn", 0) or 0),
        pins_shared=str(raw.get("pins", "")) == "shared",
        pins_reachable=bool(raw.get("pins_reachable", True)),
        repeat_captures=int(raw.get("repeat_captures", 0) or 0),
        standby_only_orders=int(raw.get("standby_only_orders", 0) or 0),
        fence_copied_to_standby=bool(raw.get("fence_copied_to_standby", False)),
        incident_orders_on_standby=bool(raw.get("incident_orders_on_standby", False)),
        process_up=bool(raw.get("process_up", True)),
    )


def probe_codes(metrics: HaMetrics) -> list[str]:
    codes: list[str] = []
    if not metrics.process_up:
        codes.append("PROCESS_DOWN")
    if not metrics.writer_ok():
        codes.append("WRITER_COUNT")
    if not metrics.lag_ok():
        codes.append("SEQ_GAP")
    if not metrics.pins_ok():
        codes.append("PINS")
    if not metrics.captures_ok():
        codes.append("REPEAT_CAPTURES")
    if int(metrics.standby_only_orders) > 0:
        codes.append("STANDBY_ONLY_ORDERS")
    if metrics.fence_copied_to_standby:
        codes.append("FENCE_ON_STANDBY")
    if not metrics.incident_orders_on_standby:
        codes.append("INCIDENT_NOT_REPLAYED")
    return codes


def as_prometheus_like(metrics: HaMetrics) -> list[str]:
    labels = ",".join(f'writer="{w}"' for w in metrics.writers) or 'writer=""'
    lines = [
        f"shopdesk_writer_count {metrics.writer_count}",
        f"shopdesk_primary_seq {metrics.primary_seq}",
        f"shopdesk_standby_seq {metrics.standby_seq}",
        f"shopdesk_seq_gap {metrics.seq_gap}",
        f"shopdesk_repeat_captures {metrics.repeat_captures}",
        f"shopdesk_accepting_checkout {1 if metrics.accepting() else 0}",
        f"shopdesk_writers{{{labels}}} 1",
    ]
    return lines


def compare_metrics(left: HaMetrics, right: HaMetrics) -> dict[str, object]:
    return {
        "writer_count_delta": right.writer_count - left.writer_count,
        "seq_gap_delta": right.seq_gap - left.seq_gap,
        "repeat_captures_delta": right.repeat_captures - left.repeat_captures,
        "accepting_flipped": left.accepting() != right.accepting(),
    }


def rollup(series: Sequence[HaMetrics]) -> dict[str, object]:
    if not series:
        return {"samples": 0}
    accepting = sum(1 for item in series if item.accepting())
    return {
        "samples": len(series),
        "accepting_samples": accepting,
        "max_seq_gap": max(item.seq_gap for item in series),
        "max_repeat_captures": max(item.repeat_captures for item in series),
        "max_writer_count": max(item.writer_count for item in series),
    }


def writers_from_rows(rows: Iterable[Mapping[str, object]]) -> list[str]:
    out: list[str] = []
    for row in rows:
        if int(row.get("writable", 0) or 0) != 1:
            continue
        node = str(row.get("owner_node", "")).strip().lower()
        if node and node not in out:
            out.append(node)
    return out


def readiness_bools(metrics: HaMetrics) -> dict[str, bool]:
    return {
        "process_up": metrics.process_up,
        "writer_ok": metrics.writer_ok(),
        "lag_ok": metrics.lag_ok(),
        "pins_ok": metrics.pins_ok(),
        "captures_ok": metrics.captures_ok(),
        "standby_ok": metrics.standby_ok(),
        "accepting": metrics.accepting(),
    }


def format_writer_list(writers: Sequence[str]) -> str:
    return ",".join(writers) if writers else ""


def gap_budget_remaining(metrics: HaMetrics) -> int:
    return max(0, int(metrics.max_lag_lsn) - int(metrics.seq_gap))
