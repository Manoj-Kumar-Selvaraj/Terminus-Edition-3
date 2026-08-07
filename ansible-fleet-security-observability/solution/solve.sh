#!/bin/bash
# Restore the contract Ansible tree, then apply twice for idempotency.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED="$HERE/fixed"

test -f /app/environment/docs/posture-contract.md
test -f "$FIXED/ansible/site.yml"

rm -rf /app/environment/ansible
cp -a "$FIXED/ansible" /app/environment/ansible

/app/bin/fleet-harden-apply
/app/bin/fleet-harden-apply

test -s /app/var/fleet-harden/posture-report.json
test -f /app/var/fleet-harden/stage-11.ok
