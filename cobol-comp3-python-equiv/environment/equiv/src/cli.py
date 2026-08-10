from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.layout import load_layout
from src.report import evaluate

DEFAULT_LAYOUT = Path("/app/equiv/programs/skumast.layout")
DEFAULT_RECORDS = Path("/app/equiv/samples/sku-public.dat")
DEFAULT_OUT = Path("/app/equiv/out/equivalence-report.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="equiv-eval")
    parser.add_argument("--layout", default=str(DEFAULT_LAYOUT))
    parser.add_argument("--records", default=str(DEFAULT_RECORDS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        return code
    layout = load_layout(args.layout)
    blob = Path(args.records).read_bytes()
    report = evaluate(layout, blob, args.records)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["summary"]["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
