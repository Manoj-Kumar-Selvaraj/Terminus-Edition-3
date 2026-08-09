#!/usr/bin/env bash
set -euo pipefail
ROOT="${CONTINUITY_ROOT:-/app/continuity}"
install -m 0644 /solution/files/engine.py "$ROOT/continuity/engine.py"
install -m 0644 /solution/files/continuity.json "$ROOT/config/continuity.json"
"$ROOT/.venv/bin/python" -m py_compile \
  "$ROOT/continuity/model.py" \
  "$ROOT/continuity/store.py" \
  "$ROOT/continuity/policy.py" \
  "$ROOT/continuity/engine.py" \
  "$ROOT/continuity/runtime.py" \
  "$ROOT/continuity/cli.py" \
  "$ROOT/continuity/starter_cli.py"
