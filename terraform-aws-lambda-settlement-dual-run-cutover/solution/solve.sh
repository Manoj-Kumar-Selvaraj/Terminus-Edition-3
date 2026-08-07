#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/internal /app/terraform /app/cmd/settlementctl
mkdir -p /app/internal /app/terraform /app/cmd
cp -a "${SCRIPT_DIR}/internal/." /app/internal/
cp -a "${SCRIPT_DIR}/terraform/." /app/terraform/
cp -a "${SCRIPT_DIR}/cmd/settlementctl/." /app/cmd/settlementctl/
cp -f "${SCRIPT_DIR}/go.mod" /app/go.mod

if [[ ! -f /app/cmd/settlementctl/main.go ]]; then
  echo "settlementctl source missing" >&2
  exit 1
fi

/app/bin/settlement-dual-run
FIRST="$(python3 -c 'import json;print(json.load(open("/app/output/cutover-report.json"))["report_digest"])')"
/app/bin/settlement-dual-run
SECOND="$(python3 -c 'import json;print(json.load(open("/app/output/cutover-report.json"))["report_digest"])')"
test "$FIRST" = "$SECOND"
