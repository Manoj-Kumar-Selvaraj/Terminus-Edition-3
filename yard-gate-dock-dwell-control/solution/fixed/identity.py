"""Visit identity: SCAC/trailer parse and open-visit lookup."""

from __future__ import annotations

import re
import sqlite3
from typing import Optional

from yard.codes import EQUIPMENT, VISIT_OPEN, VISIT_TYPES
from yard.store import fetchone

SCAC_RE = re.compile(r"^[A-Z]{4}$")
TRAILER_RE = re.compile(r"^[A-Z0-9]{1,12}$")


def normalize_scac(value: str) -> Optional[str]:
    text = (value or "").strip().upper()
    if not SCAC_RE.fullmatch(text):
        return None
    return text


def normalize_trailer(value: str) -> Optional[str]:
    text = (value or "").strip().upper().replace(" ", "")
    if not TRAILER_RE.fullmatch(text):
        return None
    return text


def normalize_visit_type(value: str) -> Optional[str]:
    text = (value or "").strip().upper()
    if text not in VISIT_TYPES:
        return None
    return text


def normalize_equipment(value: str) -> Optional[str]:
    text = (value or "").strip().upper()
    if text not in EQUIPMENT:
        return None
    return text


def open_visit_for_unit(con: sqlite3.Connection, scac: str, trailer: str) -> Optional[sqlite3.Row]:
    return fetchone(
        con,
        "SELECT * FROM visits WHERE scac = ? AND trailer_number = ? "
        "AND state IN ('ON_YARD','MOVING','DOCKED')",
        (scac, trailer),
    )


def conflict_open_visit(con: sqlite3.Connection, scac: str, trailer: str) -> Optional[str]:
    row = open_visit_for_unit(con, scac, trailer)
    if row is None:
        return None
    return VISIT_OPEN
