#!/bin/bash
# Restore fixed Terraform (and edgectl if drifted), then apply twice.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED="$HERE/fixed"

test -f /app/environment/docs/cutover-contract.md
test -f "$FIXED/terraform/main.tf"

rm -rf /app/environment/terraform
cp -a "$FIXED/terraform" /app/environment/terraform

# Keep control-plane sources aligned with the fixed tree when present.
if [[ -d "$FIXED/edgectl" ]]; then
  rm -rf /app/environment/edgectl
  cp -a "$FIXED/edgectl" /app/environment/edgectl
fi

/app/bin/edge-cutover-apply
/app/bin/edge-cutover-apply

test -s /app/var/edge/cutover-seal.json
