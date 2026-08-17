"""Deterministic visit identifiers."""

from __future__ import annotations

import hashlib


def make_visit_id(scac: str, trailer: str, event_id: str) -> str:
    digest = hashlib.sha256(f"{scac}|{trailer}|{event_id}".encode("utf-8")).hexdigest()
    return "V" + digest[:12].upper()


def make_move_id(event_id: str, visit_id: str) -> str:
    digest = hashlib.sha256(f"{event_id}|{visit_id}".encode("utf-8")).hexdigest()
    return "M" + digest[:12].upper()


def make_hold_token(visit_id: str, hold_code: str, placed_at: str) -> str:
    digest = hashlib.sha256(f"{visit_id}|{hold_code}|{placed_at}".encode("utf-8")).hexdigest()
    return "H" + digest[:10].upper()
