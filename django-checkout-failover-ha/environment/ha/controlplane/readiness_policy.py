"""Readiness composition for Shopdesk /readyz versus dump accepting_checkout.

Liveness means the process answers. Live /readyz is the traffic gate: one writer,
seq gap inside budget, pins reachable, and no repeat capture rows. Dump
``accepting_checkout`` adds standby coverage and shared-pin requirements.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class ReadinessInput:
    process_up: bool
    writable_nodes: Sequence[str]
    seq_gap: int
    max_lag_lsn: int
    pins_shared: bool
    pins_reachable: bool
    repeat_captures: int
    standby_only_orders: int
    fence_copied_to_standby: bool
    incident_orders_on_standby: bool


@dataclass(frozen=True)
class ReadinessFinding:
    code: str
    severity: str
    detail: str


@dataclass
class ReadinessResult:
    accepting_checkout: bool
    findings: list[ReadinessFinding] = field(default_factory=list)

    def codes(self) -> list[str]:
        return [f.code for f in self.findings]


LIVE_READYZ_CODES = frozenset(
    {"PROCESS_DOWN", "WRITER_COUNT", "SEQ_GAP", "PINS", "REPEAT_CAPTURES"}
)


def _collect_findings(data: ReadinessInput, *, include_dump_gates: bool) -> list[ReadinessFinding]:
    findings: list[ReadinessFinding] = []
    if not data.process_up:
        findings.append(
            ReadinessFinding("PROCESS_DOWN", "blocker", "process is not answering")
        )
    writers = [n for n in data.writable_nodes if n]
    if len(writers) != 1:
        findings.append(
            ReadinessFinding(
                "WRITER_COUNT",
                "blocker",
                f"expected one writer, saw {writers!r}",
            )
        )
    if int(data.seq_gap) > int(data.max_lag_lsn):
        findings.append(
            ReadinessFinding(
                "SEQ_GAP",
                "blocker",
                f"seq_gap {data.seq_gap} exceeds budget {data.max_lag_lsn}",
            )
        )
    if not data.pins_reachable:
        findings.append(
            ReadinessFinding(
                "PINS",
                "blocker",
                "sticky pin store must be reachable",
            )
        )
    if int(data.repeat_captures) > 0:
        findings.append(
            ReadinessFinding(
                "REPEAT_CAPTURES",
                "blocker",
                f"repeat capture effects={data.repeat_captures}",
            )
        )
    if include_dump_gates:
        if not data.pins_shared:
            findings.append(
                ReadinessFinding(
                    "PINS_SHARED",
                    "blocker",
                    "dump accepting_checkout requires pins=shared",
                )
            )
        if int(data.standby_only_orders) > 0:
            findings.append(
                ReadinessFinding(
                    "STANDBY_ONLY_ORDERS",
                    "blocker",
                    f"standby_only_orders={data.standby_only_orders}",
                )
            )
        if data.fence_copied_to_standby:
            findings.append(
                ReadinessFinding(
                    "FENCE_ON_STANDBY",
                    "blocker",
                    "standby lease must not be writable after sync",
                )
            )
        if not data.incident_orders_on_standby:
            findings.append(
                ReadinessFinding(
                    "INCIDENT_NOT_REPLAYED",
                    "blocker",
                    "incident-window orders missing on standby",
                )
            )
    return findings


def evaluate_live_readyz(data: ReadinessInput) -> ReadinessResult:
    findings = _collect_findings(data, include_dump_gates=False)
    return ReadinessResult(accepting_checkout=data.process_up and not findings, findings=findings)


def evaluate_dump_accepting(data: ReadinessInput) -> ReadinessResult:
    findings = _collect_findings(data, include_dump_gates=True)
    return ReadinessResult(accepting_checkout=data.process_up and not findings, findings=findings)


def evaluate_readiness(data: ReadinessInput) -> ReadinessResult:
    """Compatibility alias: full dump-style accepting conjunction."""
    return evaluate_dump_accepting(data)


def liveness_ok(process_up: bool) -> bool:
    return bool(process_up)


def ready_http_status(result: ReadinessResult) -> int:
    return 200 if result.accepting_checkout else 503


def health_http_status(process_up: bool) -> int:
    return 200 if liveness_ok(process_up) else 503


def summarize_for_dump(result: ReadinessResult, data: ReadinessInput) -> dict[str, object]:
    writers = list(data.writable_nodes)
    return {
        "accepting_checkout": bool(result.accepting_checkout),
        "writers_seen": writers,
        "double_primary": len(writers) > 1,
        "seq_gap": int(data.seq_gap),
        "repeat_captures": int(data.repeat_captures),
        "standby_only_orders": int(data.standby_only_orders),
        "fence_copied_to_standby": bool(data.fence_copied_to_standby),
        "incident_orders_on_standby": bool(data.incident_orders_on_standby),
        "pins": "shared" if data.pins_shared else ("local" if data.pins_reachable else "missing"),
        "findings": [
            {"code": f.code, "severity": f.severity, "detail": f.detail}
            for f in result.findings
        ],
    }


def merge_writer_lists(*groups: Iterable[str]) -> list[str]:
    out: list[str] = []
    for group in groups:
        for node in group:
            text = str(node).strip().lower()
            if text and text not in out:
                out.append(text)
    return out


def readiness_blocker_summary(result: ReadinessResult) -> str:
    if result.accepting_checkout:
        return "ok"
    if not result.findings:
        return "not_accepting"
    return ",".join(f.code for f in result.findings)


def from_failover_payload(payload: Mapping[str, object], *, max_lag_lsn: int) -> ReadinessInput:
    writers = [str(w) for w in list(payload.get("writers_seen") or [])]
    pins = str(payload.get("pins", ""))
    return ReadinessInput(
        process_up=True,
        writable_nodes=writers,
        seq_gap=int(payload.get("seq_gap", 0) or 0),
        max_lag_lsn=int(max_lag_lsn),
        pins_shared=pins == "shared",
        pins_reachable=pins in {"shared", "local"},
        repeat_captures=int(payload.get("repeat_captures", 0) or 0),
        standby_only_orders=int(payload.get("standby_only_orders", 0) or 0),
        fence_copied_to_standby=bool(payload.get("fence_copied_to_standby", False)),
        incident_orders_on_standby=bool(payload.get("incident_orders_on_standby", False)),
    )


def evaluate_payload(payload: Mapping[str, object], *, max_lag_lsn: int) -> ReadinessResult:
    return evaluate_dump_accepting(from_failover_payload(payload, max_lag_lsn=max_lag_lsn))


def evaluate_live_payload(payload: Mapping[str, object], *, max_lag_lsn: int) -> ReadinessResult:
    return evaluate_live_readyz(from_failover_payload(payload, max_lag_lsn=max_lag_lsn))


def only_liveness_findings(result: ReadinessResult) -> bool:
    return result.codes() == ["PROCESS_DOWN"]


def has_blocker(result: ReadinessResult, code: str) -> bool:
    return code in result.codes()


def is_live_blocker(code: str) -> bool:
    return code in LIVE_READYZ_CODES
