"""Fulfillment / capture webhook pipeline helpers.

Exactly-one capture effect per ``attempt_id`` is the production invariant.
Starter ``controlplane.idempotency`` may still create duplicates under dual-AZ
replay; this module defines claim states and delivery bookkeeping.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping


class ClaimState(str, Enum):
    NEW = "new"
    EXISTING = "existing"
    CONFLICT = "conflict"
    BLOCKED_UNCOMMITTED = "blocked_uncommitted"


@dataclass(frozen=True)
class CaptureClaim:
    attempt_id: str
    kind: str
    payload_hash: str
    write_lsn: int
    state: ClaimState
    created: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def payload_hash_for(order_ref: str, attempt_id: str, total_cents: int) -> str:
    payload = {
        "attempt_id": attempt_id,
        "order_ref": order_ref,
        "total_cents": int(total_cents),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def decide_claim(
    *,
    existing_hashes: Mapping[str, str],
    attempt_id: str,
    kind: str,
    payload_hash: str,
    write_lsn: int,
    min_committed_lsn: int | None,
) -> CaptureClaim:
    if min_committed_lsn is not None and int(write_lsn) > int(min_committed_lsn):
        return CaptureClaim(
            attempt_id=attempt_id,
            kind=kind,
            payload_hash=payload_hash,
            write_lsn=int(write_lsn),
            state=ClaimState.BLOCKED_UNCOMMITTED,
            created=False,
        )
    key = f"{attempt_id}:{kind}"
    prior = existing_hashes.get(key)
    if prior is None:
        return CaptureClaim(
            attempt_id=attempt_id,
            kind=kind,
            payload_hash=payload_hash,
            write_lsn=int(write_lsn),
            state=ClaimState.NEW,
            created=True,
        )
    if prior != payload_hash:
        return CaptureClaim(
            attempt_id=attempt_id,
            kind=kind,
            payload_hash=payload_hash,
            write_lsn=int(write_lsn),
            state=ClaimState.CONFLICT,
            created=False,
        )
    return CaptureClaim(
        attempt_id=attempt_id,
        kind=kind,
        payload_hash=payload_hash,
        write_lsn=int(write_lsn),
        state=ClaimState.EXISTING,
        created=False,
    )


def delivery_attempt_record(
    *,
    target: str,
    attempt_no: int,
    http_status: int,
) -> dict[str, object]:
    return {
        "target": target,
        "attempt_no": int(attempt_no),
        "http_status": int(http_status),
        "at": _utc_now(),
    }


def duplicate_count(rows: list[tuple[str, str]]) -> int:
    """rows are (attempt_id, kind) pairs including duplicates."""
    seen: dict[tuple[str, str], int] = {}
    for attempt_id, kind in rows:
        key = (attempt_id, kind)
        seen[key] = seen.get(key, 0) + 1
    return sum(n - 1 for n in seen.values() if n > 1)


def should_emit_webhook(claim: CaptureClaim) -> bool:
    return claim.state == ClaimState.NEW and claim.created
