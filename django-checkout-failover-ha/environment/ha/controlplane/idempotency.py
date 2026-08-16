"""Capture side-effect claim helpers."""
from __future__ import annotations

from dataclasses import dataclass

from fulfill.models import SideEffect


@dataclass
class Claim:
    row: SideEffect
    created: bool


def claim_side_effect(*, attempt_id: str, kind: str, payload_hash: str, write_lsn: int) -> Claim:
    row = SideEffect.objects.create(
        attempt_id=attempt_id,
        kind=kind,
        payload_hash=payload_hash,
        status="PENDING",
        delivered_at=None,
        write_lsn=write_lsn,
    )
    return Claim(row=row, created=True)
