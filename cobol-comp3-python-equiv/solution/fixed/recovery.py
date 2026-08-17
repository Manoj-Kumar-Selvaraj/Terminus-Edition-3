from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import sqlite3
from .models import Checkpoint,GenerationIdentity,RunState
from .checkpoint import validate_checkpoint
from .state_machine import resumable

class RecoveryAction(str,Enum):
    START="START"
    RESUME="RESUME"
    RECONCILE="RECONCILE"
    NOOP="NOOP"
    BLOCK="BLOCK"
@dataclass(frozen=True)
class RecoveryPlan:
    action:RecoveryAction
    next_sequence:int
    byte_offset:int
    reason:str

def plan(identity:GenerationIdentity,state:RunState|None,checkpoint:Checkpoint|None,published:bool)->RecoveryPlan:
    if published:return RecoveryPlan(RecoveryAction.NOOP,0,0,"generation already published")
    if state is None and checkpoint is None:return RecoveryPlan(RecoveryAction.START,1,0,"new generation")
    if checkpoint is not None:
        try:validate_checkpoint(identity,checkpoint)
        except ValueError as exc:return RecoveryPlan(RecoveryAction.BLOCK,0,0,str(exc))
    if state==RunState.PUBLISHED:return RecoveryPlan(RecoveryAction.NOOP,0,0,"generation marked published")
    if state==RunState.READY:return RecoveryPlan(RecoveryAction.RECONCILE,(checkpoint.last_sequence+1 if checkpoint else 1),(checkpoint.byte_offset if checkpoint else 0),"revalidate controls before publication")
    if state and resumable(state):return RecoveryPlan(RecoveryAction.RESUME,(checkpoint.last_sequence+1 if checkpoint else 1),(checkpoint.byte_offset if checkpoint else 0),f"resume {state.value.lower()} generation")
    if state==RunState.CREATED:return RecoveryPlan(RecoveryAction.START,1,0,"created generation has no durable work")
    return RecoveryPlan(RecoveryAction.BLOCK,0,0,"inconsistent recovery state")
def database_plan(db:sqlite3.Connection,identity:GenerationIdentity)->RecoveryPlan:
    s=db.execute("SELECT state FROM runs WHERE generation_id=?",(identity.generation_id,)).fetchone();state=RunState(s[0]) if s else None
    c=db.execute("SELECT generation_id,last_sequence,byte_offset,source_fingerprint,updated_at FROM checkpoints WHERE generation_id=?",(identity.generation_id,)).fetchone();checkpoint=Checkpoint(*c) if c else None
    published=state==RunState.PUBLISHED
    return plan(identity,state,checkpoint,published)
def assert_no_checkpoint_gap(db:sqlite3.Connection,generation_id:str)->None:
    c=db.execute("SELECT last_sequence FROM checkpoints WHERE generation_id=?",(generation_id,)).fetchone()
    if not c:return
    max_seq=db.execute("SELECT COALESCE(MAX(sequence),0) FROM processed_movements WHERE generation_id=?",(generation_id,)).fetchone()[0]
    if int(c[0])>int(max_seq):raise ValueError("checkpoint is ahead of durable movement state")
def durable_sequence(db:sqlite3.Connection,generation_id:str)->int:
    return int(db.execute("SELECT COALESCE(MAX(sequence),0) FROM processed_movements WHERE generation_id=?",(generation_id,)).fetchone()[0])
def incomplete_sequences(db:sqlite3.Connection,generation_id:str)->list[int]:
    rows=[int(r[0]) for r in db.execute("SELECT sequence FROM processed_movements WHERE generation_id=? ORDER BY sequence",(generation_id,))]
    if not rows:return []
    return sorted(set(range(1,max(rows)+1))-set(rows))
