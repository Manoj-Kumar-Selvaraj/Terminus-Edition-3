#!/usr/bin/env bash
set -euo pipefail

cd /app/eod
repair_patch="$(mktemp)"
cat \
  /solution/repair.part1.patch \
  /solution/repair.part2.patch \
  /solution/repair.part3.patch \
  /solution/repair.part4.patch \
  > "$repair_patch"
patch -p1 < "$repair_patch"
rm -f "$repair_patch"

python3 /solution/apply_runtime_fixes.py
cat /solution/schema_guards.sql >> /app/eod/sql/schema.sql

chmod +x /app/eod/bin/run_eod.sh /app/eod/lib/*.sh
rm -rf /app/eod/.bin /app/eod/out
mkdir -p /app/eod/.bin /app/eod/out /app/eod/state
/app/eod/bin/run_eod.sh
