from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config import load_config
from src.engine.empty import apply_empty_check
from src.engine.pipeline import process_events
from src.ingest.decoder import read_events
from src.ingest.order import order_for_mode
from src.metrics.counters import RunCounters
from src.ops.finalize import finalize_run
from src.tenancy.directory import TenantDirectory
from src.paths import (
    CONFIG_PATH,
    JOURNAL_PATH,
    LATE_OUT,
    OPEN_SESSIONS_PATH,
    REJECTS_OUT,
    SESSIONS_OUT,
)
from src.sinks.jsonl import append_jsonl, truncate_jsonl
from src.state.recover import load_state


def _reset_outputs() -> None:
    for path in (SESSIONS_OUT, LATE_OUT, REJECTS_OUT):
        truncate_jsonl(path)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="run-sessions", add_help=True)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--feed", type=Path, default=None)
    parser.add_argument("--reset-output", action="store_true")
    parser.add_argument("--empty-check", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        return code if code else 0

    if args.input is None and args.feed is None and not args.empty_check:
        print("error: --input, --feed, or --empty-check required", file=sys.stderr)
        return 2

    directory = TenantDirectory.load()
    if not directory.catalog_ready():
        print("error: operator catalog unavailable", file=sys.stderr)
        return 2

    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_OUT.parent.mkdir(parents=True, exist_ok=True)
    if args.reset_output:
        _reset_outputs()

    cfg = load_config(CONFIG_PATH)
    state = load_state(JOURNAL_PATH, OPEN_SESSIONS_PATH)
    counters = RunCounters()

    if args.empty_check and args.input is None and args.feed is None:
        apply_empty_check(SESSIONS_OUT, LATE_OUT, OPEN_SESSIONS_PATH, state)
        finalize_run(counters, state, cfg, directory)
        return 0

    source = args.feed if args.feed is not None else args.input
    if source is None:
        print("error: --input, --feed, or --empty-check required", file=sys.stderr)
        return 2

    events, rejects = read_events(source)
    counters.rejected = len(rejects)
    counters.source_path = str(source)
    counters.feed_mode = args.feed is not None
    for rej in rejects:
        append_jsonl(REJECTS_OUT, rej)

    ordered = order_for_mode(events, feed=args.feed is not None)
    if not ordered and not rejects:
        apply_empty_check(SESSIONS_OUT, LATE_OUT, OPEN_SESSIONS_PATH, state)
        finalize_run(counters, state, cfg, directory)
        return 0

    process_events(
        ordered,
        cfg,
        state,
        SESSIONS_OUT,
        LATE_OUT,
        JOURNAL_PATH,
        OPEN_SESSIONS_PATH,
        counters,
        use_arrival_gap=False,
        directory=directory,
    )
    finalize_run(counters, state, cfg, directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
