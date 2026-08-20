#!/bin/bash
set -euo pipefail

solution_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target="${EDGE_ROUTER_ROOT:-/app/edge-router}"

test -d "$target"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

cat "$solution_dir"/payload.* | base64 --decode | xz --decompress > "$work/oracle.tar"
tar -xf "$work/oracle.tar" -C "$target"

cd "$target"
gofmt -w ./cmd ./internal
go test ./...
go build -o edge-router-runtime ./cmd/edge-router-runtime
