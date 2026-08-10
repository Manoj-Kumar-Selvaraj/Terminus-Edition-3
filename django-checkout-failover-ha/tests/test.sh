#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"
if [ -x /opt/ha-venv/bin/python3 ] && /opt/ha-venv/bin/python3 -c "import pytest" >/dev/null 2>&1; then
  PY=/opt/ha-venv/bin/python3
else
  PY=python3
fi
"$PY" -m pytest "$TEST_DIR" -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
