from __future__ import annotations

from pathlib import Path

ROOT = Path("/app/sessions")
CONFIG_PATH = ROOT / "config" / "processor.json"
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
JOURNAL_PATH = DATA_DIR / "watermark.journal"
OPEN_SESSIONS_PATH = DATA_DIR / "open_sessions.json"
SESSIONS_OUT = OUTPUT_DIR / "sessions.jsonl"
LATE_OUT = OUTPUT_DIR / "late.jsonl"
REJECTS_OUT = OUTPUT_DIR / "rejects.jsonl"
