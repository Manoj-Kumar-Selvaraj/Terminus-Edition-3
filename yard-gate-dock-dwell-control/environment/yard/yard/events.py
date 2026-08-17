"""Canonical event payload (used by a correct fence; starter does not hash it)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


PAYLOAD_KEYS = (
    "verb",
    "scac",
    "trailer",
    "trailer_number",
    "visit_type",
    "equipment",
    "at",
    "appointment_id",
    "spot_id",
    "door_id",
    "seal",
    "on_ground",
    "visit_id",
    "dest_spot_id",
    "move_id",
    "hold_code",
    "chassis_id",
    "as_of",
)


def canonical_payload(flags: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for key in PAYLOAD_KEYS:
        if key in flags and flags[key] is not None:
            body[key] = flags[key]
    body["verb"] = flags.get("verb")
    return body


def payload_hash(flags: dict[str, Any]) -> str:
    body = canonical_payload(flags)
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def payloads_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return canonical_payload(left) == canonical_payload(right)
