#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"
PII_HOME="${PII_HOME:-/app/enterprise-pii}"
if [ -x "$PII_HOME/scripts/build.sh" ]; then
  (cd "$PII_HOME" && ./scripts/build.sh)
fi
pytest --ctrf /logs/verifier/ctrf.json "$TEST_DIR/test_outputs.py" -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
