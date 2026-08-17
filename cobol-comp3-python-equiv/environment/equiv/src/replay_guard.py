from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import sqlite3

@dataclass(frozen=True)
class ReplayDecision:
    duplicate:bool
    same_generation:bool
    prior_generation:str|None
    reason:str

def commercial_key(item_id:str,movement_type:str,quantity:str,source:str|None,destination:str|None)->str:
    payload='|'.join([item_id,movement_type,quantity,source or '',destination or ''])
    return sha256(payload.encode()).hexdigest()
def exact_identity(generation_id:str,movement_id:str)->str:return sha256(f'{generation_id}|{movement_id}'.encode()).hexdigest()
class ReplayGuard:
    def __init__(self,db:sqlite3.Connection):self.db=db
    def exact_seen(self,generation_id:str,movement_id:str)->bool:
        return self.db.execute('SELECT 1 FROM processed_movements WHERE generation_id=? AND movement_id=?',(generation_id,movement_id)).fetchone() is not None
    def movement_history(self,movement_id:str)->list[tuple[str,str,int]]:
        return [(r[0],r[1],int(r[2])) for r in self.db.execute('SELECT generation_id,status,sequence FROM processed_movements WHERE movement_id=? ORDER BY rowid',(movement_id,))]
    def decision(self,generation_id:str,movement_id:str)->ReplayDecision:
        rows=self.movement_history(movement_id)
        if not rows:return ReplayDecision(False,False,None,'no prior exact movement identity')
        if any(g==generation_id for g,_,_ in rows):return ReplayDecision(True,True,generation_id,'movement already durable in current generation')
        prior=rows[-1][0]
        return ReplayDecision(False,False,prior,'same business movement id belongs to a different generation and is not current-generation replay')
    def assert_not_current_replay(self,generation_id:str,movement_id:str)->None:
        d=self.decision(generation_id,movement_id)
        if d.duplicate:raise ValueError(d.reason)
    def generation_duplicates(self,generation_id:str)->list[str]:
        return [r[0] for r in self.db.execute('SELECT movement_id FROM processed_movements WHERE generation_id=? GROUP BY movement_id HAVING COUNT(*)>1',(generation_id,))]
    def sequence_duplicates(self,generation_id:str)->list[int]:
        return [int(r[0]) for r in self.db.execute('SELECT sequence FROM processed_movements WHERE generation_id=? GROUP BY sequence HAVING COUNT(*)>1',(generation_id,))]
    def cross_generation_ids(self)->dict[str,list[str]]:
        out={}
        for mid,gid in self.db.execute('SELECT movement_id,generation_id FROM processed_movements ORDER BY movement_id,generation_id'):
            out.setdefault(mid,[]).append(gid)
        return {k:v for k,v in out.items() if len(set(v))>1}
    def replay_health(self,generation_id:str)->dict[str,object]:
        movement_dups=self.generation_duplicates(generation_id);sequence_dups=self.sequence_duplicates(generation_id)
        return {'generation_id':generation_id,'movement_duplicates':movement_dups,'sequence_duplicates':sequence_dups,'healthy':not movement_dups and not sequence_dups}
