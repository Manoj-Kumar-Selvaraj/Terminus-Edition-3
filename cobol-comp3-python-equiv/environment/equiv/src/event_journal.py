from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from hashlib import sha256
import json,sqlite3

@dataclass(frozen=True)
class JournalEvent:
    event_id:int
    generation_id:str
    sequence:int
    event_type:str
    subject:str
    payload_json:str
    previous_hash:str
    event_hash:str
    occurred_at:str

def ensure_table(db:sqlite3.Connection)->None:
    db.execute('CREATE TABLE IF NOT EXISTS event_journal(event_id INTEGER PRIMARY KEY AUTOINCREMENT,generation_id TEXT NOT NULL,sequence INTEGER NOT NULL,event_type TEXT NOT NULL,subject TEXT NOT NULL,payload_json TEXT NOT NULL,previous_hash TEXT NOT NULL,event_hash TEXT NOT NULL UNIQUE,occurred_at TEXT NOT NULL)')
def canonical(generation_id:str,sequence:int,event_type:str,subject:str,payload_json:str,previous_hash:str,occurred_at:str)->bytes:return '|'.join([generation_id,str(sequence),event_type,subject,payload_json,previous_hash,occurred_at]).encode()
def append(db:sqlite3.Connection,generation_id:str,sequence:int,event_type:str,subject:str,payload:dict[str,object])->JournalEvent:
    ensure_table(db);row=db.execute('SELECT event_hash FROM event_journal WHERE generation_id=? ORDER BY event_id DESC LIMIT 1',(generation_id,)).fetchone();prev=row[0] if row else '0'*64;payload_json=json.dumps(payload,sort_keys=True,separators=(',',':'),default=str);ts=datetime.now(timezone.utc).isoformat();digest=sha256(canonical(generation_id,sequence,event_type,subject,payload_json,prev,ts)).hexdigest();cur=db.execute('INSERT INTO event_journal(generation_id,sequence,event_type,subject,payload_json,previous_hash,event_hash,occurred_at) VALUES(?,?,?,?,?,?,?,?)',(generation_id,sequence,event_type,subject,payload_json,prev,digest,ts));return JournalEvent(cur.lastrowid,generation_id,sequence,event_type,subject,payload_json,prev,digest,ts)
def events(db:sqlite3.Connection,generation_id:str)->list[JournalEvent]:
    ensure_table(db);return [JournalEvent(*r) for r in db.execute('SELECT event_id,generation_id,sequence,event_type,subject,payload_json,previous_hash,event_hash,occurred_at FROM event_journal WHERE generation_id=? ORDER BY event_id',(generation_id,))]
def verify(db:sqlite3.Connection,generation_id:str)->bool:
    prev='0'*64
    for e in events(db,generation_id):
        if e.previous_hash!=prev:return False
        if sha256(canonical(e.generation_id,e.sequence,e.event_type,e.subject,e.payload_json,e.previous_hash,e.occurred_at)).hexdigest()!=e.event_hash:return False
        prev=e.event_hash
    return True
def counts(db:sqlite3.Connection,generation_id:str)->dict[str,int]:
    ensure_table(db);return {r[0]:int(r[1]) for r in db.execute('SELECT event_type,COUNT(*) FROM event_journal WHERE generation_id=? GROUP BY event_type',(generation_id,))}
