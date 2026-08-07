#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/terraform
mkdir -p /app/terraform
cp -a "${SCRIPT_DIR}/terraform/." /app/terraform/

/app/bin/wave-rehearsal
FIRST="$(python3 -c 'import json;print(json.load(open("/app/output/rehearsal-report.json"))["report_digest"])')"
/app/bin/wave-rehearsal
SECOND="$(python3 -c 'import json;print(json.load(open("/app/output/rehearsal-report.json"))["report_digest"])')"
test "$FIRST" = "$SECOND"
