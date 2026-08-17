"""Flag checks after argparse. Empty event-id is a usage error."""

from __future__ import annotations

from typing import Any, Optional

from yard.codes import EQUIPMENT, HOLD_CODES, VISIT_TYPES
from yard.identity import normalize_equipment, normalize_scac, normalize_trailer, normalize_visit_type
from yard.timeutil import parse_instant


def require_event_id(flags: dict[str, Any]) -> Optional[str]:
    event_id = flags.get("event_id")
    if event_id is None or str(event_id).strip() == "":
        return "empty --event-id"
    return None


def require_instant(flags: dict[str, Any], key: str) -> Optional[str]:
    raw = flags.get(key)
    if not raw:
        return f"missing --{key.replace('_', '-')}"
    try:
        parse_instant(str(raw))
    except ValueError:
        return f"invalid --{key.replace('_', '-')}"
    return None


def check_gate_in(flags: dict[str, Any]) -> Optional[str]:
    err = require_event_id(flags) or require_instant(flags, "at")
    if err:
        return err
    if normalize_scac(str(flags.get("scac") or "")) is None:
        return "invalid --scac"
    if normalize_trailer(str(flags.get("trailer") or "")) is None:
        return "invalid --trailer"
    if normalize_visit_type(str(flags.get("visit_type") or "")) is None:
        return "invalid --visit-type"
    if normalize_equipment(str(flags.get("equipment") or "")) is None:
        return "invalid --equipment"
    if not flags.get("spot_id"):
        return "missing --spot-id"
    if not flags.get("appointment_id"):
        return "missing --appointment-id"
    if flags.get("visit_type") not in VISIT_TYPES and flags.get("visit_type"):
        return "invalid --visit-type"
    if flags.get("equipment") not in EQUIPMENT and flags.get("equipment"):
        return "invalid --equipment"
    return None


def check_gate_out(flags: dict[str, Any]) -> Optional[str]:
    return require_event_id(flags) or require_instant(flags, "at") or (
        None if flags.get("visit_id") else "missing --visit-id"
    )


def check_dispatch(flags: dict[str, Any]) -> Optional[str]:
    if require_event_id(flags):
        return require_event_id(flags)
    if not flags.get("visit_id"):
        return "missing --visit-id"
    if not flags.get("dest_spot_id"):
        return "missing --dest-spot-id"
    return None


def check_move_id(flags: dict[str, Any]) -> Optional[str]:
    if require_event_id(flags):
        return require_event_id(flags)
    if not flags.get("move_id"):
        return "missing --move-id"
    return None


def check_hold(flags: dict[str, Any]) -> Optional[str]:
    err = require_event_id(flags) or require_instant(flags, "at")
    if err:
        return err
    if not flags.get("visit_id"):
        return "missing --visit-id"
    if flags.get("hold_code") not in HOLD_CODES:
        return "invalid --hold-code"
    return None


def check_mount(flags: dict[str, Any]) -> Optional[str]:
    if require_event_id(flags):
        return require_event_id(flags)
    if not flags.get("visit_id"):
        return "missing --visit-id"
    if not flags.get("chassis_id"):
        return "missing --chassis-id"
    return None


def check_mutating(flags: dict[str, Any]) -> Optional[str]:
    verb = flags.get("verb")
    if verb == "gate-in":
        return check_gate_in(flags)
    if verb == "gate-out":
        return check_gate_out(flags)
    if verb == "dispatch-move":
        return check_dispatch(flags)
    if verb in {"confirm-move", "cancel-move"}:
        return check_move_id(flags)
    if verb in {"hold", "release-hold"}:
        return check_hold(flags)
    if verb == "mount-chassis":
        return check_mount(flags)
    if verb == "dismount-chassis":
        return require_event_id(flags) or (None if flags.get("visit_id") else "missing --visit-id")
    return None
