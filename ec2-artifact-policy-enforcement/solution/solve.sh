#!/usr/bin/env bash
set -euo pipefail
ROOT="${POLICYGUARD_ROOT:-/app/policyguard}"
for file in adapters.rs audit.rs cache.rs engine.rs exceptions.rs permit.rs; do
  install -m 0644 "/solution/files/$file" "$ROOT/src/$file"
done
cd "$ROOT"
cargo build --release
