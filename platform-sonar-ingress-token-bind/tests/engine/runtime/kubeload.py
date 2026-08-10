from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_kubernetes(path: Path) -> list[dict[str, Any]]:
    docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    return [doc for doc in docs if isinstance(doc, dict) and doc.get("kind")]
