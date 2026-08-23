#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOVEREIGN_LB_HOME:-/app/sovereign-lb}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "${ROOT}" ]]; then
  echo "sovereign-lb root not found: ${ROOT}" >&2
  exit 1
fi

python3 "${HERE}/repair.py" "${ROOT}"
"${ROOT}/bin/build"
printf 'oracle=installed\n'
