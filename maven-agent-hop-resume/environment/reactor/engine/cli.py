from __future__ import annotations

import json
import sys

from engine import journal, runner


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in {"run", "resume", "status"}:
        print("usage: pipe run|resume|status", file=sys.stderr)
        return 2
    command = args[0]
    if command == "status":
        print(json.dumps(journal.load_journal(), indent=2))
        return 0
    if command == "run":
        state = runner.run_new()
    else:
        state = runner.resume()
    print(json.dumps({"status": state["status"], "run_id": state["run_id"], "library": state["library"]}))
    return 0 if state["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
