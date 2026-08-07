#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/controller /app/terraform
mkdir -p /app/controller /app/terraform
cp -a "${SCRIPT_DIR}/controller/." /app/controller/
cp -a "${SCRIPT_DIR}/terraform/." /app/terraform/
cp -f "${SCRIPT_DIR}/go.mod" /app/go.mod

# Ensure fleetctl source remains present for rebuilds.
if [[ ! -f /app/cmd/fleetctl/main.go ]]; then
  echo "fleetctl source missing" >&2
  exit 1
fi

/app/bin/fenced-fleet-rollout
FIRST="$(python3 -c 'import json;print(json.load(open("/app/output/rollout-report.json"))["report_digest"])')"
/app/bin/fenced-fleet-rollout
SECOND="$(python3 -c 'import json;print(json.load(open("/app/output/rollout-report.json"))["report_digest"])')"
test "$FIRST" = "$SECOND"
