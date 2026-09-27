"""Operator CLI for case bootstrap, status, plan preview, coverage, custody, and export."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any
from .errors import ForensicError
from .fixture import seed_records
from .models import ActorContext, PlanRequest
from .service import ServiceContainer


def _context(args) -> ActorContext:
    return ServiceContainer.build().authorization.context(args.tenant, args.actor)


def _emit(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="casectl")
    parser.add_argument("--tenant", default="tenant-01")
    parser.add_argument("--actor", default="analyst-000001")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    sub.add_parser("seed")
    sub.add_parser("health")
    inventory = sub.add_parser("inventory")
    inventory.add_argument("--site")
    case = sub.add_parser("case")
    case.add_argument("case_id")
    plans = sub.add_parser("plans")
    plans.add_argument("case_id")
    plans.add_argument("--file", required=True)
    coverage = sub.add_parser("coverage")
    coverage.add_argument("case_id")
    timeline = sub.add_parser("timeline")
    timeline.add_argument("case_id")
    timeline.add_argument("--limit", type=int, default=100)
    custody = sub.add_parser("custody")
    custody.add_argument("case_id")
    custody.add_argument("--limit", type=int, default=100)
    export = sub.add_parser("export")
    export.add_argument("case_id")
    export.add_argument("--manifest-only", action="store_true")
    hold = sub.add_parser("hold")
    hold.add_argument("case_id")
    hold.add_argument("reason")
    release = sub.add_parser("release-hold")
    release.add_argument("case_id")
    release.add_argument("hold_id")
    release.add_argument("reason")
    return parser


def run(args: argparse.Namespace) -> int:
    services = ServiceContainer.build()
    if args.command == "migrate":
        _emit({"applied": services.database.migrate()})
        return 0
    if args.command == "seed":
        _emit(seed_records(services.database))
        return 0
    services.bootstrap()
    if args.command == "health":
        _emit(services.readiness.snapshot())
        return 0
    if args.command == "inventory":
        if args.site:
            _emit(services.inventory.list_endpoints(args.tenant, site_id=args.site))
        else:
            _emit(services.inventory.summarize(args.tenant))
        return 0
    context = services.authorization.context(args.tenant, args.actor)
    if args.command == "case":
        _emit(services.cases.get(context, args.case_id))
    elif args.command == "plans":
        request = PlanRequest.model_validate(json.loads(Path(args.file).read_text(encoding="utf-8")))
        _emit(services.plans.create(context, request))
    elif args.command == "coverage":
        _emit(services.coverage.summary(context, args.case_id))
    elif args.command == "timeline":
        _emit({"rows": services.coverage.timeline(context, args.case_id, limit=args.limit)})
    elif args.command == "custody":
        _emit({"rows": services.coverage.custody(context, args.case_id, limit=args.limit)})
    elif args.command == "export":
        _emit(services.exports.create(context, args.case_id, include_timeline=not args.manifest_only))
    elif args.command == "hold":
        _emit({"hold_id": services.cases.place_hold(context, args.case_id, args.reason)})
    elif args.command == "release-hold":
        _emit({"released": services.cases.release_hold(context, args.case_id, args.hold_id, args.reason)})
    else:
        raise ValueError(f"unknown command {args.command}")
    return 0


def main() -> None:
    args = build_parser().parse_args()
    try:
        raise SystemExit(run(args))
    except ForensicError as exc:
        print(json.dumps(exc.as_dict(), sort_keys=True), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
