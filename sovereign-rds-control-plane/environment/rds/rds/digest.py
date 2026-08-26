"""Canonical JSON serialization and SHA-256 digest calculation."""
import hashlib
import json
from typing import Any

def sha256_text(text: str) -> str:
    """Compute SHA-256 digest over text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def canonical_json_dump(payload: Any) -> str:
    """Dump JSON with sorted keys and compact separators."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))

def compute_stable_digest(payload: Any) -> str:
    """Compute SHA-256 digest over canonical JSON payload."""
    return sha256_text(canonical_json_dump(payload))
