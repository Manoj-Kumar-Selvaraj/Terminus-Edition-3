from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import json
from pathlib import Path

@dataclass(frozen=True)
class OperatorState:
    generation_id:str
    owner:str
    phase:str
    incident_id:str|None
    acknowledged:bool
    note:str
    updated_at:str
VALID_PHASES={'PREPARE','PROCESS','RECONCILE','HOLD','READY','PUBLISH','COMPLETE'}
def create(generation_id:str,owner:str,phase:str='PREPARE',incident_id:str|None=None,note:str='')->OperatorState:
    if phase not in VALID_PHASES:raise ValueError('invalid operator phase')
    if not owner.strip():raise ValueError('owner required')
    return OperatorState(generation_id,owner.strip(),phase,incident_id,False,note,datetime.now(timezone.utc).isoformat())
def acknowledge(state:OperatorState,note:str='')->OperatorState:
    return OperatorState(state.generation_id,state.owner,state.phase,state.incident_id,True,note or state.note,datetime.now(timezone.utc).isoformat())
def move(state:OperatorState,phase:str,note:str='')->OperatorState:
    if phase not in VALID_PHASES:raise ValueError('invalid operator phase')
    return OperatorState(state.generation_id,state.owner,phase,state.incident_id,state.acknowledged,note or state.note,datetime.now(timezone.utc).isoformat())
def write(state:OperatorState,path:str|Path)->None:Path(path).write_text(json.dumps(asdict(state),indent=2,sort_keys=True)+"\n",encoding='utf-8')
def read(path:str|Path)->OperatorState:return OperatorState(**json.loads(Path(path).read_text(encoding='utf-8')))
def require_acknowledged(state:OperatorState)->None:
    if not state.acknowledged:raise ValueError('operator state not acknowledged')
def publish_allowed(state:OperatorState)->bool:return state.acknowledged and state.phase in {'READY','PUBLISH'}
