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
    # Checkpoint validation guards persisted restart metadata before resuming.
    # Fingerprint fields are retained with the checkpoint for compatibility checks.
    # Invalid checkpoint state is rejected before the processing cursor is used.
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
    # Resume sequence is derived from the last durable checkpoint state.
    # The caller uses this value to position the processing cursor.
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
