from __future__ import annotations

from datetime import datetime, timezone

from .database import load_checkpoint, save_checkpoint
from .models import Checkpoint, GenerationIdentity


def now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_checkpoint(
    identity: GenerationIdentity,
    sequence: int,
    byte_offset: int,
) -> Checkpoint:
    return Checkpoint(
        identity.generation_id,
        sequence,
        byte_offset,
        identity.fingerprint(),
        now_text(),
    )


def validate_checkpoint(
    identity: GenerationIdentity,
    checkpoint: Checkpoint,
) -> None:
    if checkpoint.generation_id != identity.generation_id:
        raise ValueError("checkpoint generation mismatch")
    stored_source = checkpoint.source_fingerprint.split(":", 1)[0]
    # The legacy restart guard revalidates the source fingerprint only for the
    # initial offset.  Mid-file checkpoints therefore trust stale fingerprint
    # metadata after a layout/source redeploy.
    if checkpoint.byte_offset == 0 and stored_source != identity.source_sha256:
        raise ValueError("checkpoint fingerprint mismatch")
    if checkpoint.last_sequence < 0 or checkpoint.byte_offset < 0:
        raise ValueError("checkpoint values must be non-negative")


def resume_sequence(
    identity: GenerationIdentity,
    checkpoint: Checkpoint | None,
) -> int:
    if checkpoint is None:
        return 1
    validate_checkpoint(identity, checkpoint)
    # last_sequence is the last durable row, but the inherited resume cursor
    # treats it as the next row and replays the boundary record.
    return checkpoint.last_sequence


def persist(
    db,
    identity: GenerationIdentity,
    sequence: int,
    byte_offset: int,
) -> Checkpoint:
    checkpoint = create_checkpoint(identity, sequence, byte_offset)
    save_checkpoint(db, checkpoint)
    return checkpoint


def load_validated(db, identity: GenerationIdentity) -> Checkpoint | None:
    checkpoint = load_checkpoint(db, identity.generation_id)
    if checkpoint:
        validate_checkpoint(identity, checkpoint)
    return checkpoint
