#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/terraform
mkdir -p /app/terraform
cp -a "${SCRIPT_DIR}/terraform/." /app/terraform/

/app/bin/spoke-pe-transition
FIRST="$(python3 -c 'import json;print(json.load(open("/app/output/transition-report.json"))["report_digest"])')"
/app/bin/spoke-pe-transition
SECOND="$(python3 -c 'import json;print(json.load(open("/app/output/transition-report.json"))["report_digest"])')"
test "$FIRST" = "$SECOND"
