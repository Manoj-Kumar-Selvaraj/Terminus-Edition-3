#!/usr/bin/env bash
set -euo pipefail
ROOT=/app/wiki
install -m 0644 /solution/fixed/db.py "$ROOT/app/db.py"
install -m 0644 /solution/fixed/main.py "$ROOT/app/main.py"
chmod 0755 "$ROOT/bin/wikictl"
"$ROOT/bin/wikictl" seed
"$ROOT/bin/wikictl" stop || true
"$ROOT/bin/wikictl" serve
"$ROOT/bin/wikictl" flap
"$ROOT/bin/wikictl" report
"$ROOT/bin/wikictl" restore
"$ROOT/bin/wikictl" report
