#!/usr/bin/env bash
set -euo pipefail

ROOT="${ANSIBLEOPS_ROOT:-/app/ansibleops}"
WORK="$(mktemp -d /tmp/ansibleops-smoke.XXXXXX)"
cleanup() {
  rm -rf "${WORK}"
  rm -rf /tmp/ansibleops-smoke-managed
}
trap cleanup EXIT

"${ROOT}/scripts/build-provider.sh" >/dev/null
cp "${ROOT}/examples/basic/main.tf" "${WORK}/main.tf"
cd "${WORK}"
terraform init -input=false >/dev/null
terraform apply -auto-approve -input=false >/dev/null

test -d /tmp/ansibleops-smoke-managed
test -f /tmp/ansibleops-smoke-managed/config.txt
grep -qx 'managed=true' /tmp/ansibleops-smoke-managed/config.txt

terraform destroy -auto-approve -input=false >/dev/null
printf 'smoke=pass\n'
