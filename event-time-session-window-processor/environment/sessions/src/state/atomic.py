from __future__ import annotations

import json
import os
from pathlib import Path


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def atomic_write_json(path: Path, obj: object) -> None:
    payload = json.dumps(obj, separators=(",", ":"), sort_keys=True) + "\n"
    atomic_write_text(path, payload)
