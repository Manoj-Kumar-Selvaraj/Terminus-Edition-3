from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .batch_orchestrator import OrchestrationRequest, execute as execute_run
from .config import CutoverConfig, Paths
from .database import apply_sql, connect
from .generation import build_identity, input_manifest
from .layout import load_layout
from .operations import archive as archive_generation, audit as audit_generation, preflight


def _run_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--db", required=True)
    command.add_argument("--source", required=True)
    command.add_argument("--layout", required=True)
    command.add_argument("--business-date", required=True)
    command.add_argument("--legacy-controls", required=True)
    command.add_argument("--report-dir", required=True)
    command.add_argument("--publish-dir", required=True)
    command.add_argument("--stop-after", type=int)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="equiv-eval")
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init-db")
    init.add_argument("--db", required=True)
    init.add_argument("--schema", required=True)
    init.add_argument("--seed", required=True)

    describe = commands.add_parser("describe-layout")
    describe.add_argument("--layout", required=True)

    identity = commands.add_parser("identity")
    identity.add_argument("--source", required=True)
    identity.add_argument("--layout", required=True)
    identity.add_argument("--business-date", required=True)

    run = commands.add_parser("run")
    _run_arguments(run)

    check = commands.add_parser("preflight")
    _run_arguments(check)
    check.add_argument("--schema", required=True)
    check.add_argument("--seed", required=True)
    check.add_argument("--producer", default="legacy-wms")
    check.add_argument("--batch-id", default="daily-inventory-cutover")
    check.add_argument("--owner", default="warehouse-operations")
    check.add_argument("--environment", choices=("dev", "test", "stage", "prod"), default="prod")

    audit = commands.add_parser("audit")
    audit.add_argument("--db", required=True)
    audit.add_argument("--source", required=True)
    audit.add_argument("--layout", required=True)
    audit.add_argument("--business-date", required=True)
    audit.add_argument("--expected-records", required=True, type=int)
    audit.add_argument("--quarantine", required=True)
    audit.add_argument("--registry", required=True)

    archive = commands.add_parser("archive")
    archive.add_argument("--db", required=True)
    archive.add_argument("--source", required=True)
    archive.add_argument("--layout", required=True)
    archive.add_argument("--business-date", required=True)
    archive.add_argument("--report-dir", required=True)
    archive.add_argument("--publish-dir", required=True)
    archive.add_argument("--archive-dir", required=True)
    archive.add_argument("--registry", required=True)
    return root


def _emit(payload: object, *, stream=None) -> None:
    print(json.dumps(payload, sort_keys=True, default=str), file=stream or sys.stdout)


def _cutover_config(args: argparse.Namespace) -> CutoverConfig:
    report_dir = Path(args.report_dir)
    operational_root = report_dir.parent
    paths = Paths(
        Path(args.source),
        Path(args.layout),
        Path(args.db),
        Path(args.schema),
        Path(args.seed),
        Path(args.legacy_controls),
        report_dir,
        Path(args.publish_dir),
        operational_root / "audit" / "events.jsonl",
        operational_root / "quarantine" / "records.jsonl",
        operational_root / "publication-registry.jsonl",
    )
    return CutoverConfig(
        args.business_date,
        args.producer,
        args.batch_id,
        args.owner,
        args.environment,
        paths,
    )


def _execute(args: argparse.Namespace) -> tuple[object, int]:
    if args.command == "init-db":
        db = connect(args.db)
        apply_sql(db, args.schema)
        apply_sql(db, args.seed)
        return {"initialized": str(Path(args.db)), "status": "READY"}, 0

    if args.command == "describe-layout":
        layout = load_layout(args.layout)
        return {
            "layout_id": layout.layout_id,
            "version": layout.version,
            "minimum_length": layout.static_min_length(),
            "fingerprint": layout.fingerprint(),
        }, 0

    if args.command == "identity":
        return input_manifest(
            build_identity(args.source, args.layout, args.business_date)
        ), 0

    if args.command == "run":
        db = connect(args.db)
        request = OrchestrationRequest(
            Path(args.db),
            Path(args.source),
            Path(args.layout),
            args.business_date,
            Path(args.legacy_controls),
            Path(args.report_dir),
            Path(args.publish_dir),
            args.stop_after,
        )
        summary = execute_run(db, request)
        return summary.as_dict(), 0 if summary.state.value in {"READY", "PUBLISHED"} else 2

    if args.command == "preflight":
        db = connect(args.db)
        result = preflight(db, _cutover_config(args))
        return result, 0 if result["passed"] else 2

    if args.command == "audit":
        db = connect(args.db)
        result = audit_generation(
            db,
            Path(args.source),
            Path(args.layout),
            args.business_date,
            args.expected_records,
            Path(args.quarantine),
            Path(args.registry),
        )
        return result, 0 if result["passed"] else 2

    if args.command == "archive":
        db = connect(args.db)
        result = archive_generation(
            db,
            Path(args.source),
            Path(args.layout),
            args.business_date,
            Path(args.report_dir),
            Path(args.publish_dir),
            Path(args.archive_dir),
            Path(args.registry),
        )
        return result, 0 if result["passed"] else 2

    raise ValueError(f"unsupported command {args.command}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        payload, status = _execute(args)
    except (ValueError, PermissionError, FileNotFoundError, sqlite3.Error) as exc:
        _emit(
            {"error": {"type": exc.__class__.__name__, "message": str(exc)}},
            stream=sys.stderr,
        )
        return 2
    _emit(payload)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
