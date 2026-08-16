#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"

APP="${OUTBOX_ROOT:-/app/outbox}"
if [ -d "$APP" ]; then
  (
    cd "$APP" || exit 1
    go mod tidy >/tmp/outbox-tidy.log 2>&1 || true
    go build -o "$APP/bin/outboxd" ./cmd/outboxd
    go build -o "$APP/bin/outboxctl" ./cmd/outboxctl
  )
fi

python3 -m pytest --ctrf /logs/verifier/ctrf.json \
  "$TEST_DIR/test_outputs.py" \
  "$TEST_DIR/test_f2p_core.py" \
  "$TEST_DIR/test_f2p_claim_delivery.py" \
  "$TEST_DIR/test_f2p_quota_audit.py" \
  "$TEST_DIR/test_f2p_replay_ui.py" \
  "$TEST_DIR/test_p2p_preserve.py" \
  -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
