#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/terraform /app/cells
mkdir -p /app/terraform /app/cells
cp -a "${SCRIPT_DIR}/terraform/." /app/terraform/
cp -a "${SCRIPT_DIR}/cells/." /app/cells/

/app/bin/cell-upgrade
FIRST="$(python3 -c 'import json;print(json.load(open("/app/output/cell-upgrade-report.json"))["report_digest"])')"
/app/bin/cell-upgrade
SECOND="$(python3 -c 'import json;print(json.load(open("/app/output/cell-upgrade-report.json"))["report_digest"])')"
test "$FIRST" = "$SECOND"
