from __future__ import annotations
from datetime import datetime, timezone
from .database import load_checkpoint, save_checkpoint
from .models import Checkpoint, GenerationIdentity

def now_text()->str: return datetime.now(timezone.utc).isoformat()
def create_checkpoint(identity:GenerationIdentity,sequence:int,byte_offset:int)->Checkpoint: return Checkpoint(identity.generation_id,sequence,byte_offset,identity.fingerprint(),now_text())
def validate_checkpoint(identity:GenerationIdentity,checkpoint:Checkpoint)->None:
    if checkpoint.generation_id!=identity.generation_id: raise ValueError("checkpoint generation mismatch")
    if checkpoint.source_fingerprint!=identity.fingerprint(): raise ValueError("checkpoint fingerprint mismatch")
    if checkpoint.last_sequence<0 or checkpoint.byte_offset<0: raise ValueError("checkpoint values must be non-negative")
def resume_sequence(identity:GenerationIdentity,checkpoint:Checkpoint|None)->int:
    if checkpoint is None: return 1
    validate_checkpoint(identity,checkpoint); return checkpoint.last_sequence+1
def persist(db,identity:GenerationIdentity,sequence:int,byte_offset:int)->Checkpoint:
    c=create_checkpoint(identity,sequence,byte_offset); save_checkpoint(db,c); return c
def load_validated(db,identity:GenerationIdentity)->Checkpoint|None:
    c=load_checkpoint(db,identity.generation_id)
    if c: validate_checkpoint(identity,c)
    return c
