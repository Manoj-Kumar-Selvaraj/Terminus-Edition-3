"""Verify detached authority receipts issued outside the repository trust boundary."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

_NAMESPACE = "terminus-authority"
_SYSTEM_ALLOWED_SIGNERS = Path("/etc/terminus/authority/allowed_signers")
_ACTION_ISSUERS = {
    "HUMAN_FEEDBACK": "terminus-human-authority",
    "AUTOMATED_SOURCE": "terminus-automation-authority",
    "REVIEW_RESULT": "terminus-review-authority",
    "EXECUTION_RESULT": "terminus-execution-authority",
    "FINDING_NORMALIZATION": "terminus-finding-authority",
    "LESSON_ACTIVATION": "terminus-learning-authority",
}
_RECEIPT_FIELDS = {
    "schema_version",
    "issuer",
    "principal",
    "action",
    "claim",
    "claim_hash",
    "signature",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def authority_claim_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def signed_payload(
    *,
    issuer: str,
    principal: str,
    action: str,
    claim: Mapping[str, Any],
) -> dict[str, Any]:
    copied = _json_object(claim, "authority claim")
    return {
        "schema_version": "1.0",
        "issuer": issuer,
        "principal": principal,
        "action": action,
        "claim": copied,
        "claim_hash": authority_claim_hash(copied),
    }


class AuthorityReceiptValidator:
    """Validate an OpenSSH-signed semantic authority receipt.

    Production verification has exactly one trust root:
    /etc/terminus/authority/allowed_signers. There is deliberately no runtime,
    environment-selected or repository-selected alternate signer path.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()

    def verify(
        self,
        receipt: Mapping[str, Any] | None,
        *,
        action: str,
        principal: str,
        claim: Mapping[str, Any],
    ) -> dict[str, Any]:
        if action not in _ACTION_ISSUERS:
            raise ValueError(f"unknown authority receipt action: {action}")
        if not isinstance(receipt, Mapping):
            raise ValueError(f"{action} requires an authenticated authority receipt")
        value = _json_object(receipt, "authority receipt")
        unknown = set(value) - _RECEIPT_FIELDS
        missing = _RECEIPT_FIELDS - set(value)
        if unknown or missing:
            raise ValueError(
                "authority receipt fields are invalid: "
                f"missing={sorted(missing)} unknown={sorted(unknown)}"
            )
        if value.get("schema_version") != "1.0":
            raise ValueError("unsupported authority receipt schema_version")
        expected_issuer = _ACTION_ISSUERS[action]
        if value.get("issuer") != expected_issuer:
            raise ValueError(
                f"{action} authority receipt issuer must be {expected_issuer}"
            )
        if value.get("principal") != principal:
            raise ValueError("authority receipt principal does not match semantic owner")
        if value.get("action") != action:
            raise ValueError("authority receipt action does not match requested authority")
        expected_claim = _json_object(claim, "expected authority claim")
        if value.get("claim") != expected_claim:
            raise ValueError("authority receipt claim does not bind the exact semantic action")
        expected_hash = authority_claim_hash(expected_claim)
        if value.get("claim_hash") != expected_hash:
            raise ValueError("authority receipt claim_hash does not bind its claim")
        signature = value.get("signature")
        if not isinstance(signature, str) or not signature.strip():
            raise ValueError("authority receipt requires a detached SSH signature")
        payload = {key: value[key] for key in _RECEIPT_FIELDS if key != "signature"}
        self._verify_signature(
            issuer=expected_issuer,
            message=canonical_json(payload).encode("utf-8"),
            signature=signature,
        )
        return value

    def _allowed_signers(self) -> Path:
        if os.environ.get("TERMINUS_AUTHORITY_ALLOWED_SIGNERS") or os.environ.get(
            "TERMINUS_TEST_AUTHORITY_ALLOWED_SIGNERS"
        ):
            raise ValueError(
                "authority trust root is fixed; caller-selected signer overrides are forbidden"
            )
        path = _SYSTEM_ALLOWED_SIGNERS
        if path.is_symlink():
            raise ValueError("authority allowed-signers file must not be a symlink")
        if not path.is_file():
            raise ValueError(
                "system authority allowed-signers file is unavailable at "
                f"{path}"
            )
        metadata = path.stat()
        if metadata.st_uid != 0:
            raise ValueError("authority allowed-signers file must be owned by root")
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError(
                "authority allowed-signers file must not be group/world writable"
            )
        return path

    def _verify_signature(self, *, issuer: str, message: bytes, signature: str) -> None:
        allowed = self._allowed_signers()
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".sig", delete=False
        ) as handle:
            handle.write(signature)
            signature_path = Path(handle.name)
        try:
            try:
                result = subprocess.run(
                    [
                        "ssh-keygen",
                        "-Y",
                        "verify",
                        "-f",
                        str(allowed),
                        "-I",
                        issuer,
                        "-n",
                        _NAMESPACE,
                        "-s",
                        str(signature_path),
                    ],
                    input=message,
                    capture_output=True,
                )
            except FileNotFoundError as exc:
                raise ValueError(
                    "ssh-keygen is required to verify semantic authority receipts"
                ) from exc
            if result.returncode != 0:
                detail = result.stderr.decode("utf-8", errors="replace").strip()
                raise ValueError(
                    "authority receipt signature verification failed"
                    + (f": {detail}" if detail else "")
                )
        finally:
            signature_path.unlink(missing_ok=True)


def _json_object(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    try:
        copied = json.loads(canonical_json(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON-compatible") from exc
    if not isinstance(copied, dict):
        raise ValueError(f"{label} must be one JSON object")
    return copied
