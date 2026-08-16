#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/go/bin:${PATH:-}"

ROOT="${OUTBOX_ROOT:-/app/outbox}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED="$HERE/fixed"

install -m 0644 "$FIXED/internal/claim/claimer.go" "$ROOT/internal/claim/claimer.go"
install -m 0644 "$FIXED/internal/sign/hmac.go" "$ROOT/internal/sign/hmac.go"
install -m 0644 "$FIXED/internal/quota/window.go" "$ROOT/internal/quota/window.go"
install -m 0644 "$FIXED/internal/audit/writer.go" "$ROOT/internal/audit/writer.go"
install -m 0644 "$FIXED/internal/policy/replay.go" "$ROOT/internal/policy/replay.go"
install -m 0644 "$FIXED/ui/js/app.js" "$ROOT/ui/js/app.js"

cd "$ROOT"
go build -o "$ROOT/bin/outboxd" ./cmd/outboxd
go build -o "$ROOT/bin/outboxctl" ./cmd/outboxctl
