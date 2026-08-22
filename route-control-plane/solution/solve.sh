#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROUTECP_ROOT:-/app/routecp}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "${ROOT}" ]]; then
  echo "routecp root not found: ${ROOT}" >&2
  exit 1
fi

python3 "${HERE}/repair.py" "${ROOT}"
python3 "${HERE}/ansible_projection_fix.py" "${ROOT}"
cd "${ROOT}"
gofmt -w ./cmd ./internal
go test ./...
go build -o /tmp/routecp-oracle ./cmd/routecp
rm -f /tmp/routecp-oracle
printf 'oracle=installed\n'
