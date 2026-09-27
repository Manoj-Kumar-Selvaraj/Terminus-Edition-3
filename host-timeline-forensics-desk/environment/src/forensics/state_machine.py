"""Explicit plan, source, and export transitions."""
from __future__ import annotations
from .errors import InvalidTransition
from .models import SourceDisposition

PLAN_TRANSITIONS = {
    "draft": {"validated", "rejected"},
    "validated": {"queued", "cancelled"},
    "queued": {"running", "cancelled", "failed"},
    "running": {"reconciling", "partial", "failed", "cancelled"},
    "reconciling": {"complete", "partial", "failed"},
    "partial": {"queued", "complete", "failed", "cancelled"},
    "complete": set(), "rejected": set(), "failed": {"queued"}, "cancelled": set(),
}

SOURCE_TRANSITIONS = {
    SourceDisposition.REQUESTED: {SourceDisposition.QUEUED, SourceDisposition.REJECTED, SourceDisposition.UNAVAILABLE},
    SourceDisposition.QUEUED: {SourceDisposition.RUNNING, SourceDisposition.CANCELLED, SourceDisposition.FAILED},
    SourceDisposition.RUNNING: {SourceDisposition.COMPLETE, SourceDisposition.PARTIAL, SourceDisposition.UNAVAILABLE, SourceDisposition.REJECTED, SourceDisposition.FAILED, SourceDisposition.CANCELLED},
    SourceDisposition.PARTIAL: {SourceDisposition.RUNNING, SourceDisposition.COMPLETE, SourceDisposition.FAILED, SourceDisposition.CANCELLED},
    SourceDisposition.COMPLETE: set(),
    SourceDisposition.UNAVAILABLE: {SourceDisposition.QUEUED},
    SourceDisposition.REJECTED: set(),
    SourceDisposition.CANCELLED: set(),
    SourceDisposition.FAILED: {SourceDisposition.QUEUED},
}

EXPORT_TRANSITIONS = {
    "requested": {"authorizing", "rejected"},
    "authorizing": {"staging", "rejected", "failed"},
    "staging": {"verifying", "failed", "cancelled"},
    "verifying": {"published", "failed"},
    "published": set(), "rejected": set(), "failed": {"requested"}, "cancelled": set(),
}


def transition(current: str | SourceDisposition, target: str | SourceDisposition,
               table: dict, *, label: str) -> None:
    allowed = table.get(current)
    if allowed is None or target not in allowed:
        raise InvalidTransition(f"{label} cannot transition from {current} to {target}")


def can_advance_observation(current: str, observed: str) -> bool:
    """Starter reducer uses the transition graph to constrain event-driven updates."""
    if current in {"complete", "rejected", "cancelled"}:
        return False
    try:
        transition(current, observed, PLAN_TRANSITIONS, label="collection plan")
        return True
    except InvalidTransition:
        return False
