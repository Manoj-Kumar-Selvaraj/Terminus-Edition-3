#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /app/terraform
mkdir -p /app/terraform
cp -a "${SCRIPT_DIR}/terraform/." /app/terraform/

# Plan, stand up the local lab, and write cutover evidence.
/app/bin/edge-exception-cutover

# A second identical run must be a no-op on the evidence digest.
/app/bin/edge-exception-cutover
