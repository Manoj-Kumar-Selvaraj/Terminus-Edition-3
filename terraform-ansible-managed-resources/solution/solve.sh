#!/usr/bin/env bash
set -euo pipefail

ROOT="${ANSIBLEOPS_ROOT:-/app/provider}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED="${HERE}/fixed"

if [[ ! -d "${ROOT}" ]]; then
  echo "provider root not found: ${ROOT}" >&2
  exit 1
fi

while IFS= read -r -d '' source; do
  rel="${source#${FIXED}/}"
  target="${ROOT}/${rel}"
  install -D -m 0644 "${source}" "${target}"
done < <(find "${FIXED}" -type f -name '*.go' -print0 | sort -z)

cd "${ROOT}"
gofmt -w ./cmd ./internal
"${ROOT}/scripts/build-provider.sh" >/dev/null
printf 'oracle=installed\n'
