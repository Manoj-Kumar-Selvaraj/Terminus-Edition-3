"""Test-only helpers for generating ephemeral signed authority receipts."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from authority.receipts import canonical_json, signed_payload

_ISSUERS = {
    "HUMAN_FEEDBACK": "terminus-human-authority",
    "AUTOMATED_SOURCE": "terminus-automation-authority",
    "REVIEW_RESULT": "terminus-review-authority",
    "EXECUTION_RESULT": "terminus-execution-authority",
    "FINDING_NORMALIZATION": "terminus-finding-authority",
    "LESSON_ACTIVATION": "terminus-learning-authority",
}
_CACHE: dict[str, dict[str, Any]] = {}


def sign_receipt(
    action: str,
    principal: str,
    claim: Mapping[str, Any],
) -> dict[str, Any]:
    issuer = _ISSUERS[action]
    payload = signed_payload(
        issuer=issuer,
        principal=principal,
        action=action,
        claim=claim,
    )
    cache_key = canonical_json(payload)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return json.loads(canonical_json(cached))
    private_key = os.environ.get("TERMINUS_TEST_AUTHORITY_PRIVATE_KEY", "").strip()
    if not private_key:
        raise RuntimeError("test authority private key is not configured")
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as handle:
        handle.write(cache_key.encode("utf-8"))
        message_path = Path(handle.name)
    signature_path = Path(str(message_path) + ".sig")
    try:
        subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "sign",
                "-f",
                private_key,
                "-n",
                "terminus-authority",
                str(message_path),
            ],
            check=True,
            capture_output=True,
        )
        receipt = {**payload, "signature": signature_path.read_text(encoding="utf-8")}
        _CACHE[cache_key] = receipt
        return json.loads(canonical_json(receipt))
    finally:
        message_path.unlink(missing_ok=True)
        signature_path.unlink(missing_ok=True)
