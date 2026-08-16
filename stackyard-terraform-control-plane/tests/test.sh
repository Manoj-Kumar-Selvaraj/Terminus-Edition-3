#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"

APP="${STACKYARD_ROOT:-/app/stackyard}"
if [ -d "$APP" ]; then
  chmod 0755 "$APP/bin/terraform-shim" 2>/dev/null || true
  (
    cd "$APP" || exit 1
    go mod tidy >/tmp/stackyard-tidy.log 2>&1 || true
    go build -o "$APP/bin/stackyard" ./cmd/stackyard
  )
fi

python3 -m pytest --ctrf /logs/verifier/ctrf.json \
  "$TEST_DIR/test_outputs.py" \
  "$TEST_DIR/test_api_core.py" \
  "$TEST_DIR/test_api_runs.py" \
  "$TEST_DIR/test_api_locks.py" \
  "$TEST_DIR/test_api_secrets.py" \
  "$TEST_DIR/test_ui_smoke.py" \
  -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
