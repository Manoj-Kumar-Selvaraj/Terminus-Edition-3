from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class LineRecord:
    line_no: int
    offset: int
    text: str
    blank: bool
    utf8_ok: bool


@dataclass
class SourceScan:
    path: Path
    bytes_read: int = 0
    lines_seen: int = 0
    blank_lines: int = 0
    nonempty_lines: int = 0
    decode_errors: int = 0
    records: list[LineRecord] = field(default_factory=list)

    def summary(self) -> dict[str, int | str]:
        return {
            "path": str(self.path),
            "bytes_read": self.bytes_read,
            "lines_seen": self.lines_seen,
            "blank_lines": self.blank_lines,
            "nonempty_lines": self.nonempty_lines,
            "decode_errors": self.decode_errors,
        }


def _decode_bytes(raw: bytes) -> tuple[str, int]:
    try:
        return raw.decode("utf-8"), 0
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace"), 1


def scan_source(path: Path) -> SourceScan:
    scan = SourceScan(path=path)
    if not path.is_file():
        return scan
    raw = path.read_bytes()
    scan.bytes_read = len(raw)
    text, err = _decode_bytes(raw)
    scan.decode_errors += err
    offset = 0
    for line_no, line in enumerate(text.splitlines(keepends=True), start=1):
        body = line[:-1] if line.endswith("\n") else line
        if body.endswith("\r"):
            body = body[:-1]
        blank = body.strip() == ""
        rec = LineRecord(
            line_no=line_no,
            offset=offset,
            text=body,
            blank=blank,
            utf8_ok=err == 0,
        )
        scan.records.append(rec)
        scan.lines_seen += 1
        if blank:
            scan.blank_lines += 1
        else:
            scan.nonempty_lines += 1
        offset += len(line.encode("utf-8", errors="replace"))
    return scan


def iter_nonempty(scan: SourceScan) -> Iterator[LineRecord]:
    for rec in scan.records:
        if not rec.blank:
            yield rec


def first_nonempty_offset(scan: SourceScan) -> int | None:
    for rec in scan.records:
        if not rec.blank:
            return rec.offset
    return None


def last_nonempty_line_no(scan: SourceScan) -> int | None:
    last = None
    for rec in scan.records:
        if not rec.blank:
            last = rec.line_no
    return last
