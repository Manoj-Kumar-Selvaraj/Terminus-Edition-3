#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/go/bin:${PATH:-}"

ROOT="${CATALOG_ROOT:-/app/catalog}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED="$HERE/fixed"

install -m 0644 "$FIXED/internal/snapshot/snapshot.go" "$ROOT/internal/snapshot/snapshot.go"
install -m 0644 "$FIXED/internal/constraints/constraints.go" "$ROOT/internal/constraints/constraints.go"
install -m 0644 "$FIXED/internal/indexes/indexes.go" "$ROOT/internal/indexes/indexes.go"
install -m 0644 "$FIXED/internal/cdc/cdc.go" "$ROOT/internal/cdc/cdc.go"
install -m 0644 "$FIXED/internal/replica/replica.go" "$ROOT/internal/replica/replica.go"
install -m 0644 "$FIXED/internal/recover/recover.go" "$ROOT/internal/recover/recover.go"
install -m 0644 "$FIXED/internal/inspect/inspect.go" "$ROOT/internal/inspect/inspect.go"
install -m 0644 "$FIXED/internal/cli/cli.go" "$ROOT/internal/cli/cli.go"

cd "$ROOT"
go build -o "$ROOT/bin/catalogctl" ./cmd/catalogctl
"$ROOT/bin/catalogctl" recover
"$ROOT/bin/catalogctl" decode
"$ROOT/bin/catalogctl" inspect
test -s "$ROOT/out/health.json"
test -s "$ROOT/out/cdc.jsonl"
