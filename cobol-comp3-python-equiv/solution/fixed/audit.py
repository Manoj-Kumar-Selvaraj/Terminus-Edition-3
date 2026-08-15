from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from hashlib import sha256
import json,sqlite3
from pathlib import Path

@dataclass(frozen=True)
class AuditEvent:
    event_type:str
    generation_id:str
    sequence:int
    subject:str
    payload:dict[str,object]
    occurred_at:str
    previous_hash:str
    event_hash:str

def canonical_payload(event_type:str,generation_id:str,sequence:int,subject:str,payload:dict[str,object],occurred_at:str,previous_hash:str)->bytes:
    doc={"event_type":event_type,"generation_id":generation_id,"sequence":sequence,"subject":subject,"payload":payload,"occurred_at":occurred_at,"previous_hash":previous_hash}
    return json.dumps(doc,sort_keys=True,separators=(",",":"),default=str).encode()
def event_hash(*args)->str:return sha256(canonical_payload(*args)).hexdigest()
def now()->str:return datetime.now(timezone.utc).isoformat()
class AuditTrail:
    def __init__(self,path:str|Path):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
    def last_hash(self)->str:
        if not self.path.exists():return "0"*64
        last=""
        with self.path.open(encoding='utf-8') as f:
            for line in f:
                if line.strip():last=line
        if not last:return "0"*64
        return str(json.loads(last)["event_hash"])
    def append(self,event_type:str,generation_id:str,sequence:int,subject:str,payload:dict[str,object])->AuditEvent:
        prev=self.last_hash();ts=now();digest=event_hash(event_type,generation_id,sequence,subject,payload,ts,prev)
        event=AuditEvent(event_type,generation_id,sequence,subject,payload,ts,prev,digest)
        with self.path.open('a',encoding='utf-8') as f:f.write(json.dumps(asdict(event),sort_keys=True,default=str)+"\n")
        return event
    def events(self)->list[AuditEvent]:
        if not self.path.exists():return []
        return [AuditEvent(**json.loads(line)) for line in self.path.read_text(encoding='utf-8').splitlines() if line.strip()]
    def verify(self)->bool:
        prev="0"*64
        for e in self.events():
            if e.previous_hash!=prev:return False
            if e.event_hash!=event_hash(e.event_type,e.generation_id,e.sequence,e.subject,e.payload,e.occurred_at,e.previous_hash):return False
            prev=e.event_hash
        return True
    def generation_events(self,generation_id:str)->list[AuditEvent]:return [e for e in self.events() if e.generation_id==generation_id]
    def subject_events(self,subject:str)->list[AuditEvent]:return [e for e in self.events() if e.subject==subject]
    def event_counts(self)->dict[str,int]:
        out={}
        for e in self.events():out[e.event_type]=out.get(e.event_type,0)+1
        return out
    def export_summary(self)->dict[str,object]:
        events=self.events();return {"events":len(events),"valid_chain":self.verify(),"first_hash":events[0].event_hash if events else None,"last_hash":events[-1].event_hash if events else None,"types":self.event_counts()}
