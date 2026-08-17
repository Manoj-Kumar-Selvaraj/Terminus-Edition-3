"""Operator CLI. Parse and reject usage before touching journal, sqlite, or out files."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Optional

from yard import journal, publish, replay, store
from yard.argcheck import check_mutating
from yard.codes import OK_EXIT, USAGE_EXIT
from yard.engine import apply_mutating
from yard.paths import Paths
from yard.policy import Policy
from yard.timeutil import parse_instant


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yardctl", add_help=True, exit_on_error=False)
    sub = parser.add_subparsers(dest="verb")

    def add_event(p: argparse.ArgumentParser) -> None:
        p.add_argument("--event-id", dest="event_id", default=None)

    gin = sub.add_parser("gate-in")
    add_event(gin)
    gin.add_argument("--scac")
    gin.add_argument("--trailer")
    gin.add_argument("--visit-type", dest="visit_type")
    gin.add_argument("--equipment")
    gin.add_argument("--at")
    gin.add_argument("--appointment-id", dest="appointment_id")
    gin.add_argument("--spot-id", dest="spot_id")
    gin.add_argument("--door-id", dest="door_id")
    gin.add_argument("--seal")
    gin.add_argument("--on-ground", dest="on_ground", type=int)

    gout = sub.add_parser("gate-out")
    add_event(gout)
    gout.add_argument("--visit-id", dest="visit_id")
    gout.add_argument("--at")
    gout.add_argument("--seal")

    disp = sub.add_parser("dispatch-move")
    add_event(disp)
    disp.add_argument("--visit-id", dest="visit_id")
    disp.add_argument("--dest-spot-id", dest="dest_spot_id")

    conf = sub.add_parser("confirm-move")
    add_event(conf)
    conf.add_argument("--move-id", dest="move_id")

    canc = sub.add_parser("cancel-move")
    add_event(canc)
    canc.add_argument("--move-id", dest="move_id")

    hold = sub.add_parser("hold")
    add_event(hold)
    hold.add_argument("--visit-id", dest="visit_id")
    hold.add_argument("--hold-code", dest="hold_code")
    hold.add_argument("--at")

    rel = sub.add_parser("release-hold")
    add_event(rel)
    rel.add_argument("--visit-id", dest="visit_id")
    rel.add_argument("--hold-code", dest="hold_code")
    rel.add_argument("--at")

    mount = sub.add_parser("mount-chassis")
    add_event(mount)
    mount.add_argument("--visit-id", dest="visit_id")
    mount.add_argument("--chassis-id", dest="chassis_id")

    dis = sub.add_parser("dismount-chassis")
    add_event(dis)
    dis.add_argument("--visit-id", dest="visit_id")

    snap = sub.add_parser("snapshot")
    snap.add_argument("--as-of", dest="as_of")
    det = sub.add_parser("detention-run")
    det.add_argument("--as-of", dest="as_of")
    sub.add_parser("health")
    sub.add_parser("replay")
    return parser


MUTATING = {
    "gate-in",
    "gate-out",
    "dispatch-move",
    "confirm-move",
    "cancel-move",
    "hold",
    "release-hold",
    "mount-chassis",
    "dismount-chassis",
}


def _flags(ns: argparse.Namespace) -> dict[str, Any]:
    data = vars(ns)
    data["verb"] = ns.verb
    return data


def _as_of(value: Optional[str], paths: Paths) -> datetime:
    if value:
        return parse_instant(value)
    events = journal.read_events(paths.journal)
    if events:
        return parse_instant(str(events[-1].get("accepted_at") or events[-1].get("at")))
    return datetime(2026, 3, 16, 0, 0, tzinfo=timezone.utc)


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _parser()
    try:
        ns = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else USAGE_EXIT
        return 0 if code in (0, None) else USAGE_EXIT
    except argparse.ArgumentError:
        print("error: invalid arguments", file=sys.stderr)
        return USAGE_EXIT
    if not ns.verb:
        print("error: verb required", file=sys.stderr)
        return USAGE_EXIT
    if ns.verb in MUTATING:
        flags = _flags(ns)
        if not getattr(ns, "event_id", None) or str(ns.event_id).strip() == "":
            print("error: --event-id required", file=sys.stderr)
            return USAGE_EXIT
        usage = check_mutating(flags)
        if usage:
            print(f"error: {usage}", file=sys.stderr)
            return USAGE_EXIT
        paths = Paths()
        con = store.connect(paths)
        policy = Policy(paths)
        replay.replay(con, paths, policy)
        return apply_mutating(con, paths, policy, flags)[0]
    paths = Paths()
    con = store.connect(paths)
    policy = Policy(paths)
    as_of = _as_of(getattr(ns, "as_of", None), paths)
    if ns.verb == "snapshot":
        publish.snapshot(con, paths, policy, as_of)
        publish.publish_moves(con, paths)
        print(json.dumps({"ok": True, "path": str(paths.snapshot)}), flush=True)
        return OK_EXIT
    if ns.verb == "detention-run":
        publish.publish_detention(con, paths, policy, as_of)
        print(json.dumps({"ok": True, "path": str(paths.detention)}), flush=True)
        return OK_EXIT
    if ns.verb == "health":
        publish.publish_health(con, paths)
        print(json.dumps({"ok": True, "path": str(paths.health)}), flush=True)
        return OK_EXIT
    if ns.verb == "replay":
        replay.replay(con, paths, policy)
        print(json.dumps({"ok": True, "applied_seq": store.get_applied_seq(con)}), flush=True)
        return OK_EXIT
    print("error: unknown verb", file=sys.stderr)
    return USAGE_EXIT
