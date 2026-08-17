from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Iterator
from .models import Checkpoint, InventoryEffect, InventoryPosition, Movement, Reject, RunState

sqlite3.register_adapter(Decimal,lambda d:format(d,"f"))

def connect(path:str|Path)->sqlite3.Connection:
    db=sqlite3.connect(str(path)); db.row_factory=sqlite3.Row; db.execute("PRAGMA foreign_keys=ON"); db.execute("PRAGMA journal_mode=WAL"); return db

def apply_sql(db:sqlite3.Connection,path:str|Path)->None: db.executescript(Path(path).read_text(encoding="utf-8")); db.commit()

@contextmanager
def transaction(db:sqlite3.Connection)->Iterator[sqlite3.Connection]:
    db.execute("BEGIN IMMEDIATE")
    try: yield db
    except Exception: db.rollback(); raise
    else: db.commit()

def load_positions(db:sqlite3.Connection)->dict[tuple[str,str],InventoryPosition]:
    rows=db.execute("SELECT warehouse_id,item_id,quantity,value,version FROM inventory_positions").fetchall()
    return {(r["warehouse_id"],r["item_id"]):InventoryPosition(r["warehouse_id"],r["item_id"],Decimal(r["quantity"]),Decimal(r["value"]),r["version"]) for r in rows}

def get_position(db:sqlite3.Connection,warehouse_id:str,item_id:str)->InventoryPosition:
    r=db.execute("SELECT warehouse_id,item_id,quantity,value,version FROM inventory_positions WHERE warehouse_id=? AND item_id=?",(warehouse_id,item_id)).fetchone()
    return InventoryPosition(warehouse_id,item_id,Decimal("0"),Decimal("0"),0) if r is None else InventoryPosition(r["warehouse_id"],r["item_id"],Decimal(r["quantity"]),Decimal(r["value"]),r["version"])

def save_position(db:sqlite3.Connection,p:InventoryPosition)->None:
    db.execute("INSERT INTO inventory_positions(warehouse_id,item_id,quantity,value,version) VALUES(?,?,?,?,?) ON CONFLICT(warehouse_id,item_id) DO UPDATE SET quantity=excluded.quantity,value=excluded.value,version=excluded.version",(p.warehouse_id,p.item_id,str(p.quantity),str(p.value),p.version))

def movement_seen(db:sqlite3.Connection,generation_id:str,movement_id:str)->bool:
    return db.execute("SELECT 1 FROM processed_movements WHERE generation_id=? AND movement_id=?",(generation_id,movement_id)).fetchone() is not None

def insert_processed(db:sqlite3.Connection,m:Movement,status:str)->None:
    db.execute("INSERT INTO processed_movements(generation_id,movement_id,sequence,status,item_id,movement_type,quantity,unit_cost) VALUES(?,?,?,?,?,?,?,?)",(m.generation_id,m.movement_id,m.sequence,status,m.item_id,m.movement_type.value,str(m.quantity),str(m.unit_cost)))

def insert_effect(db:sqlite3.Connection,e:InventoryEffect,generation_id:str)->None:
    db.execute("INSERT INTO inventory_effects(generation_id,movement_id,sequence,warehouse_id,item_id,quantity_delta,value_delta,effect_kind) VALUES(?,?,?,?,?,?,?,?)",(generation_id,e.movement_id,e.sequence,e.warehouse_id,e.item_id,str(e.quantity_delta),str(e.value_delta),e.effect_kind))

def insert_reject(db:sqlite3.Connection,r:Reject)->None:
    db.execute("INSERT INTO rejects(generation_id,sequence,movement_id,code,message,byte_offset,byte_length) VALUES(?,?,?,?,?,?,?)",(r.generation_id,r.sequence,r.movement_id,r.code,r.message,r.byte_offset,r.byte_length))

def save_checkpoint(db:sqlite3.Connection,c:Checkpoint)->None:
    db.execute("INSERT INTO checkpoints(generation_id,last_sequence,byte_offset,source_fingerprint,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(generation_id) DO UPDATE SET last_sequence=excluded.last_sequence,byte_offset=excluded.byte_offset,source_fingerprint=excluded.source_fingerprint,updated_at=excluded.updated_at",(c.generation_id,c.last_sequence,c.byte_offset,c.source_fingerprint,c.updated_at))

def load_checkpoint(db:sqlite3.Connection,generation_id:str)->Checkpoint|None:
    r=db.execute("SELECT * FROM checkpoints WHERE generation_id=?",(generation_id,)).fetchone()
    return None if r is None else Checkpoint(r["generation_id"],r["last_sequence"],r["byte_offset"],r["source_fingerprint"],r["updated_at"])

def set_run_state(db:sqlite3.Connection,generation_id:str,state:RunState)->None:
    db.execute("INSERT INTO runs(generation_id,state) VALUES(?,?) ON CONFLICT(generation_id) DO UPDATE SET state=excluded.state",(generation_id,state.value))

def get_run_state(db:sqlite3.Connection,generation_id:str)->RunState|None:
    r=db.execute("SELECT state FROM runs WHERE generation_id=?",(generation_id,)).fetchone(); return None if r is None else RunState(r["state"])

def count_processed(db:sqlite3.Connection,generation_id:str)->int: return int(db.execute("SELECT COUNT(*) FROM processed_movements WHERE generation_id=?",(generation_id,)).fetchone()[0])
def count_rejects(db:sqlite3.Connection,generation_id:str)->int: return int(db.execute("SELECT COUNT(*) FROM rejects WHERE generation_id=?",(generation_id,)).fetchone()[0])
def effect_totals(db:sqlite3.Connection,generation_id:str)->tuple[Decimal,Decimal]:
    r=db.execute("SELECT COALESCE(SUM(CAST(quantity_delta AS REAL)),0),COALESCE(SUM(CAST(value_delta AS REAL)),0) FROM inventory_effects WHERE generation_id=?",(generation_id,)).fetchone(); return Decimal(str(r[0])),Decimal(str(r[1]))
def generation_sequences(db:sqlite3.Connection,generation_id:str)->list[int]: return [int(r[0]) for r in db.execute("SELECT sequence FROM processed_movements WHERE generation_id=? ORDER BY sequence",(generation_id,))]
def effect_rows(db:sqlite3.Connection,generation_id:str)->list[sqlite3.Row]: return db.execute("SELECT * FROM inventory_effects WHERE generation_id=? ORDER BY sequence,id",(generation_id,)).fetchall()
def reject_rows(db:sqlite3.Connection,generation_id:str)->list[sqlite3.Row]: return db.execute("SELECT * FROM rejects WHERE generation_id=? ORDER BY sequence,id",(generation_id,)).fetchall()

def seed_inventory(db:sqlite3.Connection,warehouse_count:int=8,item_count:int=1000)->None:
    with transaction(db):
        for w in range(1,warehouse_count+1):
            wid=f"W{w:02d}"; db.execute("INSERT OR IGNORE INTO warehouses(warehouse_id,active) VALUES(?,1)",(wid,))
        for i in range(1,item_count+1):
            item=f"SKU{i:05d}"; db.execute("INSERT OR IGNORE INTO items(item_id,active,max_unit_cost,quantity_precision) VALUES(?,1,'999999.99',3)",(item,))
            for w in range(1,warehouse_count+1):
                qty=Decimal(100+(i*w)%900); cost=Decimal("2.50")+Decimal((i*7+w)%500)/Decimal(10); save_position(db,InventoryPosition(f"W{w:02d}",item,qty,(qty*cost).quantize(Decimal('0.01')),1))
