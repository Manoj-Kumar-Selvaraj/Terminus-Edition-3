#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/backend
mkdir -p /app/backend /app/bin /app/var/backend-store /app/output
cp -a "${SCRIPT_DIR}/backend/." /app/backend/
cp -a "${SCRIPT_DIR}/bin/operator-apply" /app/bin/operator-apply
chmod +x /app/bin/http-backend /app/bin/operator-apply /app/bin/export-audit

# Fresh durable store for the oracle rehearsal.
rm -rf /app/var/backend-store
mkdir -p /app/var/backend-store /app/output

export BACKEND_HOST=127.0.0.1
export BACKEND_PORT=18765
export BACKEND_DATA_DIR=/app/var/backend-store
export LEASE_TTL_TICKS=10
export TF_CLI_CONFIG_FILE=/app/terraform.tfrc
export TF_IN_AUTOMATION=1
export CHECKPOINT_DISABLE=1

rm -f /app/var/backend-store/ready
python3 /app/bin/http-backend >/app/var/backend-store/backend.log 2>&1 &
BACKEND_PID=$!

cleanup() {
  kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  wait "${BACKEND_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 200); do
  if curl -sf "http://127.0.0.1:${BACKEND_PORT}/v1/control/health" >/dev/null; then
    break
  fi
  sleep 0.05
done
curl -sf "http://127.0.0.1:${BACKEND_PORT}/v1/control/health" >/dev/null

python3 /app/bin/operator-apply --workspace prod --marker oracle-prod-1
python3 /app/bin/operator-apply --workspace stage --marker oracle-stage-1
python3 /app/bin/operator-apply --workspace prod --marker oracle-prod-2
python3 /app/bin/export-audit

test -f /app/output/audit.json
test -f /app/var/backend-store/state.db
test -f /app/terraform/workspaces/prod/.terraform.lock.hcl
test -f /app/terraform/workspaces/stage/.terraform.lock.hcl
