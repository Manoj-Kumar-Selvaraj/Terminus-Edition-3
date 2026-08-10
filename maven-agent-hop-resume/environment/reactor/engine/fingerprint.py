from __future__ import annotations

import hashlib
from pathlib import Path

from engine.paths import FINGERPRINTS, SRC


def module_fingerprint(module: str) -> str:
    root = SRC / module
    h = hashlib.sha256()
    if not root.is_dir():
        return h.hexdigest()
    files = sorted(p for p in root.rglob("*") if p.is_file())
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        h.update(rel)
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def stored_fingerprint(module: str) -> str | None:
    path = FINGERPRINTS / f"{module}.sha256"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def write_fingerprint(module: str, digest: str) -> None:
    FINGERPRINTS.mkdir(parents=True, exist_ok=True)
    (FINGERPRINTS / f"{module}.sha256").write_text(digest + "\n", encoding="utf-8")
