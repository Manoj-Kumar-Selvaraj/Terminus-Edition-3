from __future__ import annotations

import hashlib
from pathlib import Path


def file_sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ledger_fingerprint(path: Path) -> dict[str, str | int]:
    digest = file_sha256(path)
    size = path.stat().st_size if path.is_file() else 0
    return {"sha256": digest, "bytes": int(size), "path": str(path)}
