#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/terraform
mkdir -p /app/terraform
cp -a "${SCRIPT_DIR}/terraform/." /app/terraform/

/app/bin/split-horizon-migrate
/app/bin/split-horizon-migrate
