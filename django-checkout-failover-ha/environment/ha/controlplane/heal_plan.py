"""Heal / cutover verification plan for Shopdesk dual-AZ checkout.

Operator dump_failover and /readyz share this checklist so traffic acceptance and
failover-status.json stay aligned on the same heal steps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence


class HealStep(str, Enum):
    SINGLE_WRITER = "single_writer"
    SEQ_IN_BUDGET = "seq_in_budget"
    PINS_REACHABLE = "pins_reachable"
    PINS_SHARED = "pins_shared"
    NO_REPEAT_CAPTURES = "no_repeat_captures"
    NO_STANDBY_ONLY = "no_standby_only"
    INCIDENT_ON_STANDBY = "incident_on_standby"
    STANDBY_LEASE_READONLY = "standby_lease_readonly"


LIVE_READYZ_STEPS = (
    HealStep.SINGLE_WRITER,
    HealStep.SEQ_IN_BUDGET,
    HealStep.PINS_REACHABLE,
    HealStep.NO_REPEAT_CAPTURES,
)

DUMP_ACCEPT_STEPS = LIVE_READYZ_STEPS + (
    HealStep.PINS_SHARED,
    HealStep.NO_STANDBY_ONLY,
    HealStep.INCIDENT_ON_STANDBY,
    HealStep.STANDBY_LEASE_READONLY,
)


@dataclass(frozen=True)
class HealObservation:
    writers: tuple[str, ...]
    seq_gap: int
    max_lag_lsn: int
    pins_reachable: bool
    pins_label: str
    repeat_captures: int
    standby_only_orders: int
    incident_orders_on_standby: bool
    fence_copied_to_standby: bool


@dataclass
class HealFinding:
    step: HealStep
    ok: bool
    detail: str


@dataclass
class HealReport:
    observations: HealObservation
    findings: list[HealFinding] = field(default_factory=list)

    def failed_steps(self) -> list[HealStep]:
        return [f.step for f in self.findings if not f.ok]

    def live_ready(self) -> bool:
        failed = set(self.failed_steps())
        return not any(step in failed for step in LIVE_READYZ_STEPS)

    def dump_accepting(self) -> bool:
        failed = set(self.failed_steps())
        return not any(step in failed for step in DUMP_ACCEPT_STEPS)

    def codes(self) -> list[str]:
        return [f.step.value for f in self.findings if not f.ok]


def evaluate_heal(obs: HealObservation) -> HealReport:
    findings: list[HealFinding] = []
    writers = tuple(w for w in obs.writers if w)
    if len(writers) != 1:
        findings.append(
            HealFinding(
                HealStep.SINGLE_WRITER,
                False,
                f"expected one writable writer, saw {list(writers)!r}",
            )
        )
    else:
        findings.append(HealFinding(HealStep.SINGLE_WRITER, True, writers[0]))
    if int(obs.seq_gap) > int(obs.max_lag_lsn):
        findings.append(
            HealFinding(
                HealStep.SEQ_IN_BUDGET,
                False,
                f"seq_gap={obs.seq_gap} exceeds budget={obs.max_lag_lsn}",
            )
        )
    else:
        findings.append(
            HealFinding(HealStep.SEQ_IN_BUDGET, True, f"seq_gap={obs.seq_gap}")
        )
    if not obs.pins_reachable:
        findings.append(
            HealFinding(HealStep.PINS_REACHABLE, False, "pins store unreachable")
        )
    else:
        findings.append(HealFinding(HealStep.PINS_REACHABLE, True, "pins reachable"))
    if obs.pins_label != "shared":
        findings.append(
            HealFinding(
                HealStep.PINS_SHARED,
                False,
                f"pins={obs.pins_label!r} (need shared)",
            )
        )
    else:
        findings.append(HealFinding(HealStep.PINS_SHARED, True, "pins=shared"))
    if int(obs.repeat_captures) > 0:
        findings.append(
            HealFinding(
                HealStep.NO_REPEAT_CAPTURES,
                False,
                f"repeat_captures={obs.repeat_captures}",
            )
        )
    else:
        findings.append(HealFinding(HealStep.NO_REPEAT_CAPTURES, True, "no repeats"))
    if int(obs.standby_only_orders) > 0:
        findings.append(
            HealFinding(
                HealStep.NO_STANDBY_ONLY,
                False,
                f"standby_only_orders={obs.standby_only_orders}",
            )
        )
    else:
        findings.append(HealFinding(HealStep.NO_STANDBY_ONLY, True, "no standby-only"))
    if not obs.incident_orders_on_standby:
        findings.append(
            HealFinding(
                HealStep.INCIDENT_ON_STANDBY,
                False,
                "incident-window orders missing on standby",
            )
        )
    else:
        findings.append(
            HealFinding(HealStep.INCIDENT_ON_STANDBY, True, "incident orders present")
        )
    if obs.fence_copied_to_standby:
        findings.append(
            HealFinding(
                HealStep.STANDBY_LEASE_READONLY,
                False,
                "standby lease still writable",
            )
        )
    else:
        findings.append(
            HealFinding(HealStep.STANDBY_LEASE_READONLY, True, "standby lease readonly")
        )
    return HealReport(observations=obs, findings=findings)


def observation_from_mapping(raw: Mapping[str, object], *, max_lag_lsn: int) -> HealObservation:
    writers = tuple(str(w) for w in list(raw.get("writers_seen") or []))
    return HealObservation(
        writers=writers,
        seq_gap=int(raw.get("seq_gap", 0) or 0),
        max_lag_lsn=int(max_lag_lsn),
        pins_reachable=bool(raw.get("pins_reachable", True)),
        pins_label=str(raw.get("pins", "missing")),
        repeat_captures=int(raw.get("repeat_captures", 0) or 0),
        standby_only_orders=int(raw.get("standby_only_orders", 0) or 0),
        incident_orders_on_standby=bool(raw.get("incident_orders_on_standby", False)),
        fence_copied_to_standby=bool(raw.get("fence_copied_to_standby", False)),
    )


def summarize_heal(report: HealReport) -> dict[str, object]:
    return {
        "live_ready": report.live_ready(),
        "dump_accepting": report.dump_accepting(),
        "failed": [s.value for s in report.failed_steps()],
        "findings": [
            {"step": f.step.value, "ok": f.ok, "detail": f.detail} for f in report.findings
        ],
    }


def remaining_operator_actions(report: HealReport) -> list[str]:
    actions: list[str] = []
    failed = set(report.failed_steps())
    if HealStep.SINGLE_WRITER in failed:
        actions.append("cutover --node <writer> and demote the other lease to writable=0")
    if HealStep.SEQ_IN_BUDGET in failed:
        actions.append("python manage.py sync_standby until seq_gap <= max_lag_lsn")
    if HealStep.PINS_REACHABLE in failed or HealStep.PINS_SHARED in failed:
        actions.append("point CACHES['pins'] at a shared file backend under state/pin-cache")
    if HealStep.NO_REPEAT_CAPTURES in failed:
        actions.append("dedupe fulfill_side_effect capture rows per attempt_id")
    if HealStep.NO_STANDBY_ONLY in failed:
        actions.append("remove or replay standby-only checkout_order rows")
    if HealStep.INCIDENT_ON_STANDBY in failed:
        actions.append("sync_standby so incident-window orders exist on standby")
    if HealStep.STANDBY_LEASE_READONLY in failed:
        actions.append("force standby ha_fence_lease.writable=0 after sync")
    return actions


def merge_failed_codes(*groups: Iterable[str]) -> list[str]:
    out: list[str] = []
    for group in groups:
        for code in group:
            text = str(code).strip()
            if text and text not in out:
                out.append(text)
    return out


def heal_progress(report: HealReport, *, dump_mode: bool = False) -> float:
    steps: Sequence[HealStep] = DUMP_ACCEPT_STEPS if dump_mode else LIVE_READYZ_STEPS
    if not steps:
        return 1.0
    ok = sum(1 for step in steps if step not in set(report.failed_steps()))
    return float(ok) / float(len(steps))
