#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "${ROOT}/output/checkpoints"
chmod 0755 "${ROOT}/bin/fluidlab" "${ROOT}/scripts/"*.sh

python3 -m compileall -q "${ROOT}/src"
"${ROOT}/bin/fluidlab" show-config --root "${ROOT}" >/dev/null
