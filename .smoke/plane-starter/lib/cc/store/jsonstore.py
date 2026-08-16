"""Atomic JSON documents and append-only JSONL journals."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterator, Mapping

from cc.util import json_line


def load_document(path: Path, default: Any) -> Any:
    """Read a JSON document, returning ``default`` when it is absent or empty."""
    if not path.is_file():
        return default
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return default
    return json.loads(text)


def save_document(path: Path, body: Any) -> None:
    """Replace a JSON document atomically so readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            json.dump(body, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def append_row(path: Path, row: Mapping[str, Any]) -> None:
    """Append one journal record, preserving the caller's key order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json_line(row))
        handle.write("\n")


def rewrite_rows(path: Path, rows: list[Mapping[str, Any]]) -> None:
    """Rewrite a journal in place; used when row state advances."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{json_line(row)}\n" for row in rows)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def iter_rows(path: Path) -> Iterator[dict[str, Any]]:
    """Yield parsed journal rows, skipping blank trailing lines."""
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                yield json.loads(text)


def read_rows(path: Path) -> list[dict[str, Any]]:
    return list(iter_rows(path))


def row_count(path: Path) -> int:
    return sum(1 for _ in iter_rows(path))
