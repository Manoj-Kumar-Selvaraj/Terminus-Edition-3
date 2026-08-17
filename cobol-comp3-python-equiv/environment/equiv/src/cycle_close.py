from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
import sqlite3
from .settlement import Settlement,require_balanced
from .state_machine import RunState

@dataclass(frozen=True)
class CloseAuthorization:
    generation_id:str
    authorized_by:str
    authorized_at:str
    settlement_processed:int
    settlement_value:str

def ensure_table(db:sqlite3.Connection)->None:
    db.execute('CREATE TABLE IF NOT EXISTS close_authorizations(generation_id TEXT PRIMARY KEY,authorized_by TEXT NOT NULL,authorized_at TEXT NOT NULL,settlement_processed INTEGER NOT NULL,settlement_value TEXT NOT NULL)')
def authorize(db:sqlite3.Connection,settlement:Settlement,actor:str)->CloseAuthorization:
    ensure_table(db);require_balanced(settlement);state=db.execute('SELECT state FROM runs WHERE generation_id=?',(settlement.generation_id,)).fetchone()
    if state is None or RunState(state[0])!=RunState.READY:raise ValueError('close authorization requires READY state')
    if not actor.strip():raise ValueError('authorizing actor required')
    existing=get(db,settlement.generation_id)
    if existing:return existing
    auth=CloseAuthorization(settlement.generation_id,actor.strip(),datetime.now(timezone.utc).isoformat(),settlement.processed,format(settlement.net_value,'f'));db.execute('INSERT INTO close_authorizations VALUES(?,?,?,?,?)',(auth.generation_id,auth.authorized_by,auth.authorized_at,auth.settlement_processed,auth.settlement_value));return auth
def get(db:sqlite3.Connection,generation_id:str)->CloseAuthorization|None:
    ensure_table(db);r=db.execute('SELECT generation_id,authorized_by,authorized_at,settlement_processed,settlement_value FROM close_authorizations WHERE generation_id=?',(generation_id,)).fetchone();return None if r is None else CloseAuthorization(*r)
def revoke(db:sqlite3.Connection,generation_id:str)->None:
    ensure_table(db);state=db.execute('SELECT state FROM runs WHERE generation_id=?',(generation_id,)).fetchone()
    if state and RunState(state[0])==RunState.PUBLISHED:raise ValueError('cannot revoke published close authorization')
    db.execute('DELETE FROM close_authorizations WHERE generation_id=?',(generation_id,))
def publication_authorized(db:sqlite3.Connection,generation_id:str)->bool:return get(db,generation_id) is not None
