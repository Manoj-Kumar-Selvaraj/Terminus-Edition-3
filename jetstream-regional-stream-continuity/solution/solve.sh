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

# Preserve the inherited incident state, but leave the requested operator snapshots behind.
# `verify` returns 2 while the captured incident state still contains unresolved data gaps;
# report materialization itself must nevertheless succeed deterministically.
set +e
"$ROOT/bin/continuityctl" verify --compact >/tmp/continuity-final-verify.json
verify_status=$?
set -e
if [[ "$verify_status" -ne 0 && "$verify_status" -ne 2 ]]; then
  exit "$verify_status"
fi
test -s "$ROOT/out/health.json"
test -s "$ROOT/out/reconciliation.json"
