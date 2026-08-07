#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/terraform /app/k8s
mkdir -p /app/terraform /app/k8s
cp -a "${SCRIPT_DIR}/terraform/." /app/terraform/
cp -a "${SCRIPT_DIR}/k8s/." /app/k8s/

/app/bin/addon-trust-rollout
FIRST="$(python3 -c 'import json;print(json.load(open("/app/output/upgrade-report.json"))["report_digest"])')"
/app/bin/addon-trust-rollout
SECOND="$(python3 -c 'import json;print(json.load(open("/app/output/upgrade-report.json"))["report_digest"])')"
test "$FIRST" = "$SECOND"
