from __future__ import annotations

import json
from pathlib import Path

from engine.paths import LIBS


def _parse_version(raw: str) -> tuple[int, ...]:
    return tuple(int(part) for part in raw.split("."))


def resolve(pin: dict) -> dict:
    # Starter: ignore the pin and take the newest directory for that library name.
    name = pin["name"]
    matches: list[Path] = []
    for manifest_path in LIBS.glob(f"{name}-*/manifest.json"):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data.get("name") == name:
            matches.append(manifest_path)
    if not matches:
        raise FileNotFoundError(f"no library named {name}")
    matches.sort(key=lambda path: _parse_version(json.loads(path.read_text(encoding="utf-8"))["version"]))
    return json.loads(matches[-1].read_text(encoding="utf-8"))
