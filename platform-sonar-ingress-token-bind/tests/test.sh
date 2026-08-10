#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"
export PLATFORM_ROOT="${PLATFORM_ROOT:-/app/platform}"
export PYTHONPATH="${PYTHONPATH:-/opt/platform-engine}"
python3 -m runtime reload >/tmp/verifier-reload.log 2>&1 || true
python3 -m runtime serve >/tmp/verifier-httpd.log 2>&1 &
echo $! > /tmp/platform-httpd.pid
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if curl -sf -H "Host: jenkins.platform.test" "http://127.0.0.1:8443/login" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done
pytest --ctrf /logs/verifier/ctrf.json "$TEST_DIR/test_outputs.py" -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
