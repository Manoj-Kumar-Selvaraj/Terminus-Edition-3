"""Mutating command application. Journal append precedes sqlite commit."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from yard import chassis, gate, holds, journal, moves, replay, store
from yard.argcheck import check_mutating
from yard.codes import EVENT_CONFLICT, OK_EXIT, REJECT_EXIT, USAGE_EXIT
from yard.events import canonical_payload
from yard.paths import Paths
from yard.policy import Policy
from yard.rejects import append_reject
from yard.timeutil import format_instant, parse_instant


def _accepted_at(flags: dict[str, Any]) -> str:
    if flags.get("at"):
        return format_instant(parse_instant(str(flags["at"])))
    return format_instant(datetime(2026, 3, 16, tzinfo=timezone.utc))


def _operator_payload(flags: dict[str, Any]) -> dict[str, Any]:
    body = canonical_payload(flags)
    verb = str(flags.get("verb") or "")
    if verb == "gate-in":
        body.pop("visit_id", None)
    if verb == "dispatch-move":
        body.pop("move_id", None)
    return body


def _stored_result(event: dict[str, Any]) -> dict[str, Any]:
    return event.get("result") if isinstance(event.get("result"), dict) else {}


def _dispatch(
    con: sqlite3.Connection,
    paths: Paths,
    policy: Policy,
    flags: dict[str, Any],
    event_id: str,
    seq: int,
) -> tuple[Optional[dict[str, Any]], Optional[str], dict[str, Any]]:
    verb = str(flags.get("verb"))
    extra: dict[str, Any] = {}
    if verb == "gate-in":
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
            seq,
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
    incoming = _operator_payload(flags)
    existing = journal.find_event(paths.journal, event_id)
    if existing is not None:
        stored = existing.get("payload")
        if not isinstance(stored, dict):
            stored = _operator_payload(existing)
        if stored != incoming:
            append_reject(paths.rejects, EVENT_CONFLICT, event_id, EVENT_CONFLICT)
            print(json.dumps({"ok": False, "code": EVENT_CONFLICT}), flush=True)
            return REJECT_EXIT, EVENT_CONFLICT, None
        result = _stored_result(existing)
        print(json.dumps({"ok": True, "seq": existing.get("seq"), "result": result, "replayed": True}), flush=True)
        return OK_EXIT, None, result

    seq = journal.next_seq(paths.journal)
    result, err, extra = _dispatch(con, paths, policy, flags, event_id, seq)
    if err == "USAGE":
        con.rollback()
        return USAGE_EXIT, err, None
    if err:
        con.rollback()
        append_reject(paths.rejects, err, event_id, err)
        print(json.dumps({"ok": False, "code": err}), flush=True)
        return REJECT_EXIT, err, None

    accepted_at = _accepted_at(flags)
    body = {key: flags[key] for key in flags if not str(key).startswith("_")}
    body.update(extra)
    body["event_id"] = event_id
    body["payload"] = incoming
    body["result"] = result
    event = journal.stamp(body, seq, accepted_at)
    journal.append_event(paths.journal, event)
    store.insert_event(con, event_id, seq, str(flags.get("verb")), json.dumps(event), accepted_at)
    store.set_applied_seq(con, seq)
    con.commit()
    replay.write_checkpoint(con, paths, seq)
    print(json.dumps({"ok": True, "seq": seq, "result": result}), flush=True)
    return OK_EXIT, None, result
