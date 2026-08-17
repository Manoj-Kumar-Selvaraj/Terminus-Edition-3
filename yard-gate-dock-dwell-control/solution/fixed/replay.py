"""Replay catch-up: apply only journal events after sqlite applied_seq."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from yard import chassis, gate, holds, journal, moves
from yard.digest import occupancy_digest
from yard.paths import Paths
from yard.policy import Policy
from yard.store import get_applied_seq, open_visits, set_applied_seq


def load_checkpoint(paths: Paths) -> dict[str, Any]:
    if not paths.checkpoint.is_file():
        return {"last_applied_seq": 0, "open_visit_ids": [], "occupancy_digest": ""}
    return json.loads(paths.checkpoint.read_text(encoding="utf-8"))


def write_checkpoint(con: sqlite3.Connection, paths: Paths, seq: int) -> None:
    open_ids = sorted(str(row["visit_id"]) for row in open_visits(con))
    payload = {
        "last_applied_seq": int(seq),
        "open_visit_ids": open_ids,
        "occupancy_digest": occupancy_digest(con),
    }
    paths.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    paths.checkpoint.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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
    applied = get_applied_seq(con)
    checkpoint = load_checkpoint(paths)
    fence = max(int(applied), int(checkpoint.get("last_applied_seq") or 0))
    for event in events:
        seq = int(event.get("seq") or 0)
        if seq <= fence:
            continue
        apply_event(con, policy, event)
        set_applied_seq(con, seq)
    con.commit()
    write_checkpoint(con, paths, get_applied_seq(con))
    return get_applied_seq(con)
