"""Replay applies the entire journal and ignores checkpoint.last_applied_seq."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from yard import chassis, gate, holds, journal, moves
from yard.paths import Paths
from yard.policy import Policy
from yard.store import get_applied_seq, set_applied_seq


def load_checkpoint(paths: Paths) -> dict[str, Any]:
    if not paths.checkpoint.is_file():
        return {"last_applied_seq": 0, "open_visit_ids": [], "occupancy_digest": ""}
    return json.loads(paths.checkpoint.read_text(encoding="utf-8"))


def apply_event(con: sqlite3.Connection, policy: Policy, event: dict[str, Any]) -> None:
    verb = str(event.get("verb") or "")
    if verb == "gate-in":
        gate.gate_in(con, policy, event)
    elif verb == "gate-out":
        gate.gate_out(con, event)
    elif verb == "dispatch-move":
        moves.dispatch(
            con,
            str(event.get("visit_id")),
            str(event.get("dest_spot_id")),
            str(event.get("event_id")),
            int(event.get("seq") or 0),
        )
    elif verb == "confirm-move":
        moves.confirm(con, str(event.get("move_id")))
    elif verb == "cancel-move":
        moves.cancel(con, str(event.get("move_id")))
    elif verb == "hold":
        holds.place(con, str(event.get("visit_id")), str(event.get("hold_code")), str(event.get("at")))
    elif verb == "release-hold":
        holds.release(con, str(event.get("visit_id")), str(event.get("hold_code")), str(event.get("at")))
    elif verb == "mount-chassis":
        chassis.mount(con, str(event.get("visit_id")), str(event.get("chassis_id")))
    elif verb == "dismount-chassis":
        chassis.dismount(con, str(event.get("visit_id")))


def replay(con: sqlite3.Connection, paths: Paths, policy: Policy) -> int:
    events = journal.read_events(paths.journal)
    _checkpoint = load_checkpoint(paths)
    _applied = get_applied_seq(con)
    for event in events:
        apply_event(con, policy, event)
        set_applied_seq(con, int(event.get("seq") or 0))
    con.commit()
    return journal.journal_head_seq(paths.journal)
