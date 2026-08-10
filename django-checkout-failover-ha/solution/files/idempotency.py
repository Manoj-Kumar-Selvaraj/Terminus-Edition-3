from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction

from fulfill.models import SideEffect


@dataclass
class Claim:
    row: SideEffect
    created: bool


def claim_side_effect(*, attempt_id: str, kind: str, payload_hash: str, write_lsn: int) -> Claim:
    existing = SideEffect.objects.using("default").filter(attempt_id=attempt_id, kind=kind).first()
    if existing is not None:
        return Claim(row=existing, created=False)
    try:
        with transaction.atomic(using="default"):
            row = SideEffect.objects.using("default").create(
                attempt_id=attempt_id,
                kind=kind,
                payload_hash=payload_hash,
                status="PENDING",
                delivered_at=None,
                write_lsn=write_lsn,
            )
        return Claim(row=row, created=True)
    except IntegrityError:
        row = SideEffect.objects.using("default").filter(attempt_id=attempt_id, kind=kind).first()
        if row is None:
            raise
        return Claim(row=row, created=False)
