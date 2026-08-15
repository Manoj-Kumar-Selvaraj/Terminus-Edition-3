from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone,timedelta
import sqlite3

@dataclass(frozen=True)
class WarehouseLock:
    warehouse_id:str
    generation_id:str
    owner:str
    acquired_at:str
    expires_at:str

def ensure_table(db:sqlite3.Connection)->None:
    db.execute('CREATE TABLE IF NOT EXISTS warehouse_locks(warehouse_id TEXT PRIMARY KEY,generation_id TEXT NOT NULL,owner TEXT NOT NULL,acquired_at TEXT NOT NULL,expires_at TEXT NOT NULL)')
def acquire(db:sqlite3.Connection,warehouse_id:str,generation_id:str,owner:str,ttl_seconds:int=900)->WarehouseLock:
    ensure_table(db);now=datetime.now(timezone.utc);expires=now+timedelta(seconds=ttl_seconds);existing=db.execute('SELECT warehouse_id,generation_id,owner,acquired_at,expires_at FROM warehouse_locks WHERE warehouse_id=?',(warehouse_id,)).fetchone()
    if existing:
        old=WarehouseLock(*existing)
        if datetime.fromisoformat(old.expires_at)>now and old.generation_id!=generation_id:raise ValueError(f'warehouse {warehouse_id} locked by {old.generation_id}')
        db.execute('DELETE FROM warehouse_locks WHERE warehouse_id=?',(warehouse_id,))
    lock=WarehouseLock(warehouse_id,generation_id,owner,now.isoformat(),expires.isoformat());db.execute('INSERT INTO warehouse_locks VALUES(?,?,?,?,?)',(lock.warehouse_id,lock.generation_id,lock.owner,lock.acquired_at,lock.expires_at));return lock
def release(db:sqlite3.Connection,warehouse_id:str,generation_id:str)->None:
    row=db.execute('SELECT generation_id FROM warehouse_locks WHERE warehouse_id=?',(warehouse_id,)).fetchone()
    if row and row[0]!=generation_id:raise ValueError('lock generation mismatch')
    db.execute('DELETE FROM warehouse_locks WHERE warehouse_id=?',(warehouse_id,))
def active(db:sqlite3.Connection,warehouse_id:str)->WarehouseLock|None:
    ensure_table(db);row=db.execute('SELECT warehouse_id,generation_id,owner,acquired_at,expires_at FROM warehouse_locks WHERE warehouse_id=?',(warehouse_id,)).fetchone()
    if row is None:return None
    lock=WarehouseLock(*row)
    if datetime.fromisoformat(lock.expires_at)<=datetime.now(timezone.utc):db.execute('DELETE FROM warehouse_locks WHERE warehouse_id=?',(warehouse_id,));return None
    return lock
def generation_locks(db:sqlite3.Connection,generation_id:str)->list[WarehouseLock]:
    ensure_table(db);return [WarehouseLock(*r) for r in db.execute('SELECT warehouse_id,generation_id,owner,acquired_at,expires_at FROM warehouse_locks WHERE generation_id=? ORDER BY warehouse_id',(generation_id,))]
