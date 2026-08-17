"""Occupancy digest used by checkpoint and health."""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Iterable

from yard.store import occupancy_rows


def digest_from_rows(rows: Iterable[sqlite3.Row | dict]) -> str:
    lines: list[str] = []
    for row in rows:
        mapping = dict(row)
        spot_id = str(mapping.get("spot_id", ""))
        visit_id = mapping.get("occupant_visit_id") or mapping.get("visit_id")
        reserved = mapping.get("reserved_move_id")
        if visit_id:
            lines.append(f"{spot_id}={visit_id}")
        elif reserved:
            lines.append(f"{spot_id}=#{reserved}")
    lines.sort()
    blob = "".join(line + "\n" for line in lines).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def occupancy_digest(con: sqlite3.Connection) -> str:
    return digest_from_rows(occupancy_rows(con))
