from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from .models import RunState

@dataclass(frozen=True)
class SafetyDecision:
    allowed:bool
    operation:str
    reason:str
DESTRUCTIVE={'RESET_DB','DELETE_PUBLICATION','TRUNCATE_AUDIT','DROP_GENERATION','VACUUM'}
def generation_state(db:sqlite3.Connection,generation_id:str)->RunState|None:
    row=db.execute('SELECT state FROM runs WHERE generation_id=?',(generation_id,)).fetchone()
    return None if row is None else RunState(row[0])
def decide(db:sqlite3.Connection,operation:str,generation_id:str|None=None,force:bool=False)->SafetyDecision:
    if operation not in DESTRUCTIVE:return SafetyDecision(True,operation,'non-destructive operation')
    if generation_id:
        state=generation_state(db,generation_id)
        if state==RunState.PUBLISHED:return SafetyDecision(False,operation,'published generation is immutable')
        if state in {RunState.PROCESSING,RunState.RECONCILING}:return SafetyDecision(False,operation,'active generation cannot be mutated')
    if not force:return SafetyDecision(False,operation,'destructive operation requires explicit force')
    return SafetyDecision(True,operation,'force accepted for non-published inactive generation')
def require(db:sqlite3.Connection,operation:str,generation_id:str|None=None,force:bool=False)->None:
    d=decide(db,operation,generation_id,force)
    if not d.allowed:raise PermissionError(d.reason)
def safe_unlink(db:sqlite3.Connection,path:str|Path,operation:str,generation_id:str|None=None,force:bool=False)->None:
    require(db,operation,generation_id,force);p=Path(path)
    if p.is_dir():raise IsADirectoryError(str(p))
    if p.exists():p.unlink()
def safe_directory_empty(db:sqlite3.Connection,path:str|Path,operation:str,generation_id:str|None=None,force:bool=False)->None:
    require(db,operation,generation_id,force);p=Path(path)
    if not p.exists():return
    for child in p.iterdir():
        if child.is_dir():raise ValueError(f'nested directory requires explicit handling: {child}')
        child.unlink()
def immutable_generation(db:sqlite3.Connection,generation_id:str)->bool:return generation_state(db,generation_id)==RunState.PUBLISHED
def describe(db:sqlite3.Connection,generation_id:str|None=None)->dict[str,object]:
    state=generation_state(db,generation_id) if generation_id else None
    return {
        'generation_id':generation_id,
        'state':state.value if state else None,
        'published_immutable':bool(state==RunState.PUBLISHED),
        'active':bool(state in {RunState.PROCESSING,RunState.RECONCILING}),
        'destructive_operations':sorted(DESTRUCTIVE),
    }

def may_reset(db:sqlite3.Connection,generation_id:str|None=None)->bool:
    return decide(db,'RESET_DB',generation_id,True).allowed
def published_mutation_blocked(db:sqlite3.Connection,generation_id:str)->bool:return immutable_generation(db,generation_id)
