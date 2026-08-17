#!/usr/bin/env bash
set -euo pipefail

cp /solution/fixed/session_key.py /app/sessions/src/keys/session_key.py
cp /solution/fixed/journal.py /app/sessions/src/state/journal.py
cp /solution/fixed/pipeline.py /app/sessions/src/engine/pipeline.py
cp /solution/fixed/cli.py /app/sessions/src/cli.py
cp /solution/fixed/watermark_track.py /app/sessions/src/runtime/watermark_track.py

rm -f /app/sessions/data/watermark.journal \
      /app/sessions/data/open_sessions.json \
      /app/sessions/output/sessions.jsonl \
      /app/sessions/output/late.jsonl \
      /app/sessions/output/rejects.jsonl

/app/sessions/bin/run-sessions --reset-output --input /app/sessions/fixtures/sample_basic.jsonl
/app/sessions/bin/run-sessions --reset-output --feed /app/sessions/fixtures/sample_late_and_reject.jsonl
