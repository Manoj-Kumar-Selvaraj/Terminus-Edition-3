#!/usr/bin/env python3
from pathlib import Path

path = Path('jetstream-regional-stream-continuity/tests/test_continuity.py')
text = path.read_text(encoding='utf-8')
old = '        assert persisted.application_sequence == 0\n'
new = '        assert persisted.application_sequence == 5600\n'
if text.count(old) != 1:
    raise SystemExit(f'unexpected restart assertion anchor count: {text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
