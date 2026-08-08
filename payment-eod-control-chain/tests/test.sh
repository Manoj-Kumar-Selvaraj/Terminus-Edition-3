#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"
python3 -m pytest "$TEST_DIR/test_outputs.py" -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
