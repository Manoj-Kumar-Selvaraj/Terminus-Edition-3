#!/usr/bin/env bash
set -euo pipefail
ROOT="${ENFORCER_ROOT:-/app/enforcer}"
install -m 0644 /solution/files/policy.go "$ROOT/internal/core/policy.go"
install -m 0644 /solution/files/store.go "$ROOT/internal/core/store.go"
install -m 0644 /solution/files/engine.go "$ROOT/internal/core/engine.go"
cd "$ROOT"
gofmt -w internal/core/policy.go internal/core/store.go internal/core/engine.go
go build -o /usr/local/bin/artifactguard ./cmd/artifactguard
