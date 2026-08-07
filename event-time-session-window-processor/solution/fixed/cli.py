from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .paths import (
    CONFIG_PATH,
    JOURNAL_PATH,
    LATE_OUT,
    OPEN_SESSIONS_PATH,
    REJECTS_OUT,
    SESSIONS_OUT,
)
from .processor import _append_jsonl, process_events, read_events, sort_for_input
from .state import load_state, save_open_sessions


def _reset_outputs() -> None:
    for path in (SESSIONS_OUT, LATE_OUT, REJECTS_OUT):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
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

    cfg = load_config(CONFIG_PATH)
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_OUT.parent.mkdir(parents=True, exist_ok=True)

    if args.reset_output:
        _reset_outputs()

    state = load_state(JOURNAL_PATH, OPEN_SESSIONS_PATH)

    if args.empty_check and args.input is None and args.feed is None:
        SESSIONS_OUT.parent.mkdir(parents=True, exist_ok=True)
        if not SESSIONS_OUT.exists():
            SESSIONS_OUT.write_text("", encoding="utf-8")
        if not LATE_OUT.exists():
            LATE_OUT.write_text("", encoding="utf-8")
        save_open_sessions(OPEN_SESSIONS_PATH, state)
        return 0

    source = args.feed if args.feed is not None else args.input
    if source is None:
        print("error: --input, --feed, or --empty-check required", file=sys.stderr)
        return 2

    events, rejects = read_events(source)
    for rej in rejects:
        _append_jsonl(REJECTS_OUT, rej)

    if args.feed is not None:
        ordered = events
    else:
        ordered = sort_for_input(events)

    if not ordered and not rejects:
        if not SESSIONS_OUT.exists():
            SESSIONS_OUT.write_text("", encoding="utf-8")
        if not LATE_OUT.exists():
            LATE_OUT.write_text("", encoding="utf-8")
        return 0

    process_events(
        ordered,
        cfg,
        state,
        SESSIONS_OUT,
        LATE_OUT,
        REJECTS_OUT,
        JOURNAL_PATH,
        OPEN_SESSIONS_PATH,
        arrival_index_for_gap=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
