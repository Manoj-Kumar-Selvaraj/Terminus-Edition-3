#!/bin/bash
set -euo pipefail
export PLATFORM_ROOT="${PLATFORM_ROOT:-/app/platform}"
fail=0
check() {
  local name="$1" url="$2" host="$3" expect="$4"
  body="$(curl -sS -H "Host: ${host}" "$url" || true)"
  if echo "$body" | grep -q "$expect"; then
    echo "ok $name"
  else
    echo "fail $name: $body"
    fail=1
  fi
}
check jenkins-login http://127.0.0.1:8443/login jenkins.platform.test jenkins-login
check sonar-status http://127.0.0.1:8443/api/system/status sonar.platform.test '"status": "UP"'
check artifactory-ping http://127.0.0.1:8443/artifactory/api/system/ping artifactory.platform.test OK
if [ -f /app/platform/var/dns/zone.json ]; then
  if grep -q jenkins.platform.test /app/platform/var/dns/zone.json; then
    echo "ok dns-zone"
  else
    echo "fail dns-zone"
    fail=1
  fi
else
  echo "fail dns-zone missing"
  fail=1
fi
exit "$fail"
