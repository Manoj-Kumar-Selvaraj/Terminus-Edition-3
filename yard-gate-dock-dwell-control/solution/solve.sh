#!/usr/bin/env bash
set -euo pipefail

ROOT="${YARD_ROOT:-/app/yard}"
FIXED="${SOLUTION_FIXED:-/solution/fixed}"

cp "$FIXED/timeutil.py" "$ROOT/yard/timeutil.py"
cp "$FIXED/policy.py" "$ROOT/yard/policy.py"
cp "$FIXED/identity.py" "$ROOT/yard/identity.py"
cp "$FIXED/appointments.py" "$ROOT/yard/appointments.py"
cp "$FIXED/inventory.py" "$ROOT/yard/inventory.py"
cp "$FIXED/doors.py" "$ROOT/yard/doors.py"
cp "$FIXED/chassis.py" "$ROOT/yard/chassis.py"
cp "$FIXED/holds.py" "$ROOT/yard/holds.py"
cp "$FIXED/moves.py" "$ROOT/yard/moves.py"
cp "$FIXED/gate.py" "$ROOT/yard/gate.py"
cp "$FIXED/detention.py" "$ROOT/yard/detention.py"
cp "$FIXED/replay.py" "$ROOT/yard/replay.py"
cp "$FIXED/publish.py" "$ROOT/yard/publish.py"
cp "$FIXED/engine.py" "$ROOT/yard/engine.py"
cp "$FIXED/cli.py" "$ROOT/yard/cli.py"
cp "$FIXED/patch_schema.py" "$ROOT/yard/patch_schema.py"

PYTHONPATH="$ROOT" YARD_ROOT="$ROOT" python3 "$ROOT/yard/patch_schema.py"
PYTHONPATH="$ROOT" YARD_ROOT="$ROOT" "$ROOT/bin/yardctl" health
PYTHONPATH="$ROOT" YARD_ROOT="$ROOT" "$ROOT/bin/yardctl" snapshot
PYTHONPATH="$ROOT" YARD_ROOT="$ROOT" "$ROOT/bin/yardctl" detention-run
