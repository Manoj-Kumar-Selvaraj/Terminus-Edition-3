"""Mutating command application. Sqlite is committed before the journal line is appended."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from yard import chassis, gate, holds, journal, moves, store
from yard.argcheck import check_mutating
from yard.codes import OK_EXIT, REJECT_EXIT, USAGE_EXIT
from yard.paths import Paths
from yard.policy import Policy
from yard.rejects import append_reject
from yard.spot_zones import drop_allowed, live_apron_required
from yard.store import get_spot
from yard.timeutil import format_instant, parse_instant


def _accepted_at(flags: dict[str, Any]) -> str:
    if flags.get("at"):
        return format_instant(parse_instant(str(flags["at"])))
    return format_instant(datetime(2026, 3, 16, tzinfo=timezone.utc))


def _dispatch(con: sqlite3.Connection, policy: Policy, flags: dict[str, Any], event_id: str) -> tuple[Optional[dict[str, Any]], Optional[str], dict[str, Any]]:
    verb = str(flags.get("verb"))
    extra: dict[str, Any] = {}
    result: Optional[dict[str, Any]] = None
    err: Optional[str] = None
    if verb == "gate-in":
        spot = get_spot(con, str(flags.get("spot_id") or ""))
        if spot is not None:
            _ = drop_allowed(str(spot["zone"]), str(flags.get("visit_type") or ""))
            _ = live_apron_required(str(flags.get("visit_type") or ""), flags.get("door_id"))
        result, err = gate.gate_in(con, policy, flags)
        if result:
            extra["visit_id"] = result["visit_id"]
        return result, err, extra
    if verb == "gate-out":
        result, err = gate.gate_out(con, flags)
        return result, err, extra
    if verb == "dispatch-move":
        move_id, err = moves.dispatch(
            con,
            str(flags.get("visit_id")),
            str(flags.get("dest_spot_id")),
            event_id,
            store.max_event_seq(con) + 1,
        )
        extra["move_id"] = move_id
        result = {"move_id": move_id} if move_id else None
        return result, err, extra
    if verb == "confirm-move":
        err = moves.confirm(con, str(flags.get("move_id")))
        result = {"move_id": flags.get("move_id")} if err is None else None
        return result, err, extra
    if verb == "cancel-move":
        err = moves.cancel(con, str(flags.get("move_id")))
        result = {"move_id": flags.get("move_id")} if err is None else None
        return result, err, extra
    if verb == "hold":
        err = holds.place(
            con,
            str(flags.get("visit_id")),
            str(flags.get("hold_code")),
            str(flags.get("at") or ""),
        )
        result = {"visit_id": flags.get("visit_id")} if err is None else None
        return result, err, extra
    if verb == "release-hold":
        err = holds.release(
            con,
            str(flags.get("visit_id")),
            str(flags.get("hold_code")),
            str(flags.get("at") or ""),
        )
        result = {"visit_id": flags.get("visit_id")} if err is None else None
        return result, err, extra
    if verb == "mount-chassis":
        err = chassis.mount(con, str(flags.get("visit_id")), str(flags.get("chassis_id")))
        result = {"visit_id": flags.get("visit_id")} if err is None else None
        return result, err, extra
    if verb == "dismount-chassis":
        err = chassis.dismount(con, str(flags.get("visit_id")))
        result = {"visit_id": flags.get("visit_id")} if err is None else None
        return result, err, extra
    return None, "USAGE", extra


def apply_mutating(
    con: sqlite3.Connection,
    paths: Paths,
    policy: Policy,
    flags: dict[str, Any],
) -> tuple[int, Optional[str], Optional[dict[str, Any]]]:
    usage = check_mutating(flags)
    if usage:
        return USAGE_EXIT, usage, None
    event_id = str(flags.get("event_id") or "")
    result, err, extra = _dispatch(con, policy, flags, event_id)
    if err == "USAGE":
        return USAGE_EXIT, err, None
    if err:
        con.commit()
        append_reject(paths.rejects, err, event_id, err)
        print(json.dumps({"ok": False, "code": err}), flush=True)
        return REJECT_EXIT, err, None
    seq = journal.next_seq(paths.journal)
    accepted_at = _accepted_at(flags)
    body = dict(flags)
    body.update(extra)
    body["event_id"] = event_id
    event = journal.stamp(body, seq, accepted_at)
    store.insert_event(con, event_id, seq, str(flags.get("verb")), json.dumps(event), accepted_at)
    store.set_applied_seq(con, seq)
    con.commit()
    journal.append_event(paths.journal, event)
    print(json.dumps({"ok": True, "seq": seq, "result": result}), flush=True)
    return OK_EXIT, None, result
