from __future__ import annotations

import json
from pathlib import Path

from engine.paths import MODULES, PIPELINE


def load_pipeline(path: Path | None = None) -> dict:
    target = path or PIPELINE
    return json.loads(target.read_text(encoding="utf-8"))


def load_modules() -> dict:
    return json.loads(MODULES.read_text(encoding="utf-8"))


def module_order(modules: dict) -> list[str]:
    order = list(modules["order"])
    graph = modules["graph"]
    seen: set[str] = set()
    for name in order:
        for dep in graph[name]:
            if dep not in seen:
                raise ValueError(f"module {name} listed before dependency {dep}")
        seen.add(name)
    return order
