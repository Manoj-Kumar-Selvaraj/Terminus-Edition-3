"""Cutover finite-state helpers for Shopdesk writer promotion.

Operator flow: sync_standby → cutover --node → dump_failover. Epoch must move
forward and the demoted node must lose ``writable``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class CutoverPhase(str, Enum):
    STEADY = "steady"
    SYNCING = "syncing"
    FENCING = "fencing"
    PROMOTED = "promoted"
    VERIFYING = "verifying"
    ABORTED = "aborted"


@dataclass
class CutoverState:
    phase: CutoverPhase = CutoverPhase.STEADY
    active_writer: str = "az-a"
    target_writer: str | None = None
    epoch: int = 1
    last_error: str | None = None
    history: list[str] = field(default_factory=list)

    def note(self, message: str) -> None:
        self.history.append(message)
        if len(self.history) > 64:
            self.history = self.history[-64:]


ALLOWED_TRANSITIONS: dict[CutoverPhase, set[CutoverPhase]] = {
    CutoverPhase.STEADY: {CutoverPhase.SYNCING, CutoverPhase.ABORTED},
    CutoverPhase.SYNCING: {CutoverPhase.FENCING, CutoverPhase.ABORTED, CutoverPhase.STEADY},
    CutoverPhase.FENCING: {CutoverPhase.PROMOTED, CutoverPhase.ABORTED},
    CutoverPhase.PROMOTED: {CutoverPhase.VERIFYING, CutoverPhase.ABORTED},
    CutoverPhase.VERIFYING: {CutoverPhase.STEADY, CutoverPhase.ABORTED},
    CutoverPhase.ABORTED: {CutoverPhase.STEADY},
}


def transition(state: CutoverState, new_phase: CutoverPhase, *, reason: str) -> CutoverState:
    allowed = ALLOWED_TRANSITIONS.get(state.phase, set())
    if new_phase not in allowed:
        state.last_error = f"illegal transition {state.phase.value} -> {new_phase.value}"
        state.note(state.last_error)
        state.phase = CutoverPhase.ABORTED
        return state
    state.phase = new_phase
    state.note(f"{new_phase.value}: {reason}")
    state.last_error = None
    return state


def begin_sync(state: CutoverState) -> CutoverState:
    return transition(state, CutoverPhase.SYNCING, reason="operator sync_standby")


def begin_fence(state: CutoverState, *, target: str) -> CutoverState:
    state.target_writer = target
    return transition(state, CutoverPhase.FENCING, reason=f"fence for {target}")


def complete_promote(state: CutoverState, *, target: str, new_epoch: int) -> CutoverState:
    if int(new_epoch) <= int(state.epoch):
        state.last_error = "epoch did not advance"
        return transition(state, CutoverPhase.ABORTED, reason=state.last_error)
    state.epoch = int(new_epoch)
    state.active_writer = target
    state.target_writer = target
    return transition(state, CutoverPhase.PROMOTED, reason=f"writer={target} epoch={new_epoch}")


def begin_verify(state: CutoverState) -> CutoverState:
    return transition(state, CutoverPhase.VERIFYING, reason="dump_failover / readyz checks")


def return_to_steady(state: CutoverState) -> CutoverState:
    return transition(state, CutoverPhase.STEADY, reason="cutover verified")


def abort(state: CutoverState, *, reason: str) -> CutoverState:
    state.last_error = reason
    state.phase = CutoverPhase.ABORTED
    state.note(f"aborted: {reason}")
    return state


def demoted_nodes(active_writer: str, known: Sequence[str]) -> list[str]:
    active = active_writer.strip().lower()
    return [n.strip().lower() for n in known if n.strip().lower() != active]


def cutover_plan(*, from_node: str, to_node: str, epoch: int) -> dict[str, object]:
    return {
        "from": from_node,
        "to": to_node,
        "required_epoch": int(epoch) + 1,
        "steps": [
            "sync_standby business tables + watermarks",
            "do not copy writable lease onto standby",
            "bump epoch and set sole writer",
            "clear demoted writable flag",
            "verify /readyz and failover-status.json",
        ],
    }
