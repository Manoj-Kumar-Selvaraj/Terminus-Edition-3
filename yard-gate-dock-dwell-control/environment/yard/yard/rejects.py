"""Reject log writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def append_reject(path: Path, code: str, event_id: Optional[str], detail: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"code": code, "event_id": event_id, "detail": detail}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")))
        handle.write("\n")
