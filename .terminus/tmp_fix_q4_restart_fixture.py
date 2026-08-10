#!/usr/bin/env python3
from pathlib import Path

path = Path('jetstream-regional-stream-continuity/tests/test_continuity.py')
text = path.read_text(encoding='utf-8')
old = '''    set_checkpoint(
        engine, "telemetry-indexer", "east", effect=0, ack=0, js_floor=0
    )
'''
new = '''    set_checkpoint(
        engine, "telemetry-indexer", "east", effect=5600, ack=5600, js_floor=5600
    )
'''
if text.count(old) != 1:
    raise SystemExit(f'unexpected restart fixture anchor count: {text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
