#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/cmd /app/terraform
mkdir -p /app/cmd /app/terraform
cp -a "${SCRIPT_DIR}/cmd/." /app/cmd/
cp -a "${SCRIPT_DIR}/terraform/." /app/terraform/
cp -a "${SCRIPT_DIR}/go.mod" /app/go.mod

cd /app
go mod tidy
go build -o /app/bin/vpc-reconcile ./cmd/vpcreconcile

# Reset durable state for a clean oracle run.
rm -rf /app/var/reconcile
mkdir -p /app/var/reconcile /app/output

# Stop any prior control-plane and clear PID file so the launcher starts fresh.
if [[ -f /app/var/reconcile/controlplane.pid ]]; then
  kill "$(cat /app/var/reconcile/controlplane.pid)" 2>/dev/null || true
fi
pkill -f "python.*-m controlplane" 2>/dev/null || true
sleep 0.3

/app/bin/vpc-reconcile-run
FIRST="$(python3 -c 'import json;print(json.load(open("/app/output/reconciliation-report.json"))["report_digest"])')"
/app/bin/vpc-reconcile-run
SECOND="$(python3 -c 'import json;print(json.load(open("/app/output/reconciliation-report.json"))["report_digest"])')"
test "$FIRST" = "$SECOND"
