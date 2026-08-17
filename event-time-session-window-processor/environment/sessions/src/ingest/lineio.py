from __future__ import annotations

from pathlib import Path
from typing import Iterator


def strip_utf8_bom(raw: bytes) -> bytes:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:]
    return raw


def decode_utf8(raw: bytes) -> tuple[str, str | None]:
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError as exc:
        return raw.decode("utf-8", errors="replace"), f"utf-8 decode error: {exc.reason}"


def read_source_text(path: Path) -> tuple[str, str | None]:
    if not path.is_file():
        return "", f"missing file: {path}"
    return decode_utf8(strip_utf8_bom(path.read_bytes()))


def iter_source_lines(path: Path) -> Iterator[tuple[int, str]]:
    text, _err = read_source_text(path)
    for line_no, line in enumerate(text.splitlines(), start=1):
        yield line_no, line


def is_blank_line(line: str) -> bool:
    return not line.strip()
