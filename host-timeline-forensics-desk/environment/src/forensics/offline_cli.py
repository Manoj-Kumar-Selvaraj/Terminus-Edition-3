"""Command-line validator/importer for signed synthetic offline bundles."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .errors import ForensicError
from .service import ServiceContainer


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="offline-intake")
    root.add_argument("bundle", type=Path)
    root.add_argument("--tenant", required=True)
    root.add_argument("--actor", required=True)
    root.add_argument("--signature", required=True)
    root.add_argument("--inspect", action="store_true")
    return root


def main() -> None:
    args = parser().parse_args()
    services = ServiceContainer.build()
    services.bootstrap()
    try:
        if args.inspect:
            result = services.offline_intake.inspect(args.bundle)
        else:
            context = services.authorization.context(args.tenant, args.actor)
            result = services.offline_intake.ingest(context, args.bundle, signature=args.signature)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2, default=str))
    except ForensicError as exc:
        print(json.dumps(exc.as_dict(), sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
    finally:
        services.database.close()


if __name__ == "__main__":
    main()
