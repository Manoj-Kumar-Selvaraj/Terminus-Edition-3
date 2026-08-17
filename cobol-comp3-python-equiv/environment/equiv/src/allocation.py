from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3
from .models import InventoryPosition
from .database import get_position

@dataclass(frozen=True)
class Allocation:
    generation_id:str
    movement_id:str
    warehouse_id:str
    item_id:str
    requested:Decimal
    available:Decimal
    allocated:Decimal
    shortfall:Decimal
    status:str

def ensure_table(db:sqlite3.Connection)->None:
    db.execute('CREATE TABLE IF NOT EXISTS allocations(generation_id TEXT NOT NULL,movement_id TEXT NOT NULL,warehouse_id TEXT NOT NULL,item_id TEXT NOT NULL,requested TEXT NOT NULL,allocated TEXT NOT NULL,status TEXT NOT NULL,PRIMARY KEY(generation_id,movement_id,warehouse_id,item_id))')
def reserved(db:sqlite3.Connection,warehouse_id:str,item_id:str,exclude_generation:str|None=None)->Decimal:
    ensure_table(db);sql="SELECT COALESCE(SUM(CAST(allocated AS REAL)),0) FROM allocations WHERE warehouse_id=? AND item_id=? AND status='ACTIVE'";args=[warehouse_id,item_id]
    if exclude_generation is not None:sql+=' AND generation_id<>?';args.append(exclude_generation)
    return Decimal(str(db.execute(sql,tuple(args)).fetchone()[0] or 0))
def available(db:sqlite3.Connection,warehouse_id:str,item_id:str,generation_id:str|None=None)->Decimal:
    position=get_position(db,warehouse_id,item_id);return max(Decimal('0'),position.quantity-reserved(db,warehouse_id,item_id,generation_id))
def plan(db:sqlite3.Connection,generation_id:str,movement_id:str,warehouse_id:str,item_id:str,requested:Decimal)->Allocation:
    avail=available(db,warehouse_id,item_id,generation_id);allocated=min(requested,avail);short=max(Decimal('0'),requested-allocated);status='FULL' if short==0 else ('PARTIAL' if allocated>0 else 'NONE');return Allocation(generation_id,movement_id,warehouse_id,item_id,requested,avail,allocated,short,status)
def persist(db:sqlite3.Connection,allocation:Allocation)->None:
    ensure_table(db);status='ACTIVE' if allocation.allocated>0 else 'NONE';db.execute('INSERT INTO allocations(generation_id,movement_id,warehouse_id,item_id,requested,allocated,status) VALUES(?,?,?,?,?,?,?) ON CONFLICT(generation_id,movement_id,warehouse_id,item_id) DO UPDATE SET requested=excluded.requested,allocated=excluded.allocated,status=excluded.status',(allocation.generation_id,allocation.movement_id,allocation.warehouse_id,allocation.item_id,str(allocation.requested),str(allocation.allocated),status))
def release(db:sqlite3.Connection,generation_id:str,movement_id:str)->None:
    ensure_table(db);db.execute("UPDATE allocations SET status='RELEASED' WHERE generation_id=? AND movement_id=?",(generation_id,movement_id))
def generation_allocations(db:sqlite3.Connection,generation_id:str)->list[Allocation]:
    ensure_table(db);rows=[]
    for r in db.execute('SELECT movement_id,warehouse_id,item_id,requested,allocated,status FROM allocations WHERE generation_id=? ORDER BY movement_id',(generation_id,)):
        requested=Decimal(r[3]);allocated=Decimal(r[4]);rows.append(Allocation(generation_id,r[0],r[1],r[2],requested,available(db,r[1],r[2],generation_id),allocated,max(Decimal('0'),requested-allocated),r[5]))
    return rows
