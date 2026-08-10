from __future__ import annotations

import argparse
import json
import sys

from .httpd import LISTEN_HOST, LISTEN_PORT, serve
from .reconcile import reload_platform


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="platform-runtime")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reload")
    sub.add_parser("serve")
    args = parser.parse_args(argv)
    if args.cmd == "reload":
        live = reload_platform()
        json.dump({"sonar_up": live.get("sonar_up"), "bound": bool(live.get("bound_token"))}, sys.stdout)
        sys.stdout.write("\n")
        return 0
    reload_platform()
    server = serve(LISTEN_HOST, LISTEN_PORT)
    print(f"platform-ingress listening on {LISTEN_HOST}:{LISTEN_PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
