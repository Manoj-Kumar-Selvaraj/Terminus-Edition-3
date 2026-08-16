#!/usr/bin/env bash
set -euo pipefail

ROOT="${STACKYARD_ROOT:-/app/stackyard}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED="$HERE/fixed"

install -m 0644 "$FIXED/internal/policy/policy.go" "$ROOT/internal/policy/policy.go"
install -m 0644 "$FIXED/internal/audit/writer.go" "$ROOT/internal/audit/writer.go"
install -m 0644 "$FIXED/ui/js/app.js" "$ROOT/ui/js/app.js"

cd "$ROOT"
go build -o "$ROOT/bin/stackyard" ./cmd/stackyard
