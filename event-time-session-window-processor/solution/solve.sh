#!/usr/bin/env bash
set -euo pipefail

# Oracle installs the corrected modules, then exercises the public operator CLI.
cp /solution/fixed/processor.py /app/sessions/src/processor.py
cp /solution/fixed/state.py /app/sessions/src/state.py
cp /solution/fixed/cli.py /app/sessions/src/cli.py

rm -f /app/sessions/data/watermark.journal \
      /app/sessions/data/open_sessions.json \
      /app/sessions/output/sessions.jsonl \
      /app/sessions/output/late.jsonl \
      /app/sessions/output/rejects.jsonl

/app/sessions/bin/run-sessions --reset-output --input /app/sessions/fixtures/sample_basic.jsonl
/app/sessions/bin/run-sessions --reset-output --feed /app/sessions/fixtures/sample_late_and_reject.jsonl
