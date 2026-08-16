#!/usr/bin/env bash
set -euo pipefail
ROOT="${OUTBOX_ROOT:-/app/outbox}"
cd "$ROOT"
./bin/seed
