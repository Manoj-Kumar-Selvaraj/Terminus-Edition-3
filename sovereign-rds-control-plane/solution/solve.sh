#!/usr/bin/env bash
set -euo pipefail

ROOT="${RDS_HOME:-/app/rds}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERLAYS="${HERE}/overlays"

if [[ ! -d "${ROOT}" ]]; then
  echo "RDS root not found: ${ROOT}" >&2
  exit 1
fi

if [[ ! -d "${OVERLAYS}/rds" ]]; then
  echo "Solution overlays missing: ${OVERLAYS}/rds" >&2
  exit 1
fi

mkdir -p "${ROOT}/rds" "${ROOT}/out" "${ROOT}/state/checkpoints"

# Apply corrected module overlays onto the control-plane package.
shopt -s nullglob
for src in "${OVERLAYS}/rds"/*.py; do
  base="$(basename "${src}")"
  dest="${ROOT}/rds/${base}"
  cp -f "${src}" "${dest}"
done
shopt -u nullglob

export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export RDS_HOME="${ROOT}"

# Prefer live estate generation when Postgres is reachable; otherwise publish offline.
python3 "${HERE}/publish_outputs.py"

echo "oracle=applied"
