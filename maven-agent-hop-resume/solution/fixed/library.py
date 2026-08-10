from __future__ import annotations

import json

from engine.paths import LIBS


def resolve(pin: dict) -> dict:
    name = pin["name"]
    version = pin["version"]
    manifest_path = LIBS / f"{name}-{version}" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("name") != name or str(data.get("version")) != str(version):
        raise ValueError(f"library manifest does not match pin {name}@{version}")
    return data
