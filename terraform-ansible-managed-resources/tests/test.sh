#!/usr/bin/env bash
set -uo pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

ROOT="${ANSIBLEOPS_ROOT:-/app/provider}"
PLUGIN_DIR="/opt/terraform/plugins/registry.terraform.io/local/ansibleops/0.1.0/linux_amd64"
PLUGIN_BIN="${PLUGIN_DIR}/terraform-provider-ansibleops_v0.1.0"

if [ ! -d "${ROOT}" ] || [ ! -f "${ROOT}/go.mod" ] || [ ! -d "${ROOT}/vendor" ]; then
  echo "provider artifact or vendored dependencies missing under ${ROOT}" >&2
  exit 1
fi

mkdir -p "${PLUGIN_DIR}"
cat >/tmp/terraform.rc <<'EOF'
provider_installation {
  filesystem_mirror {
    path    = "/opt/terraform/plugins"
    include = ["registry.terraform.io/local/ansibleops"]
  }
  direct {
    exclude = ["registry.terraform.io/local/ansibleops"]
  }
}
EOF

(
  cd "${ROOT}" || exit 1
  GOTOOLCHAIN=local go build -mod=vendor -trimpath \
    -ldflags "-s -w -X main.version=0.1.0" \
    -o "${PLUGIN_BIN}" ./cmd/terraform-provider-ansibleops
) || exit 1
chmod 0755 "${PLUGIN_BIN}"

python3 -m pytest --ctrf /logs/verifier/ctrf.json \
  /tests/test_outputs.py \
  /tests/test_provider_contract.py \
  /tests/test_lifecycle_filesystem.py \
  /tests/test_lifecycle_content.py \
  /tests/test_lifecycle_identity.py \
  /tests/test_lifecycle_delete.py \
  /tests/test_runner_and_cron.py \
  /tests/test_q4_remediation.py \
  -rA
status=$?

if [ ${status} -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit ${status}
