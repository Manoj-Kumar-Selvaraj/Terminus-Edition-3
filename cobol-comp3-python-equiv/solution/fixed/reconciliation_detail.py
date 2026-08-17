from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3

@dataclass(frozen=True)
class ReconciliationFinding:
    code:str
    movement_id:str|None
    warehouse_id:str|None
    item_id:str|None
    expected:Decimal|None
    actual:Decimal|None
    detail:str

def findings(db:sqlite3.Connection,generation_id:str)->list[ReconciliationFinding]:
    out=[]
    for r in db.execute("SELECT p.movement_id FROM processed_movements p LEFT JOIN inventory_effects e ON e.generation_id=p.generation_id AND e.movement_id=p.movement_id WHERE p.generation_id=? AND p.status='ACCEPTED' GROUP BY p.movement_id HAVING COUNT(e.id)=0",(generation_id,)):
        out.append(ReconciliationFinding('MISSING_EFFECT',r[0],None,None,Decimal(1),Decimal(0),'accepted movement has no inventory effect'))
    for r in db.execute("SELECT movement_id,ROUND(SUM(CAST(quantity_delta AS REAL)),3),ROUND(SUM(CAST(value_delta AS REAL)),2) FROM inventory_effects WHERE generation_id=? AND effect_kind LIKE 'TRANSFER_%' GROUP BY movement_id HAVING ABS(SUM(CAST(quantity_delta AS REAL)))>0.0001 OR ABS(SUM(CAST(value_delta AS REAL)))>0.01",(generation_id,)):
        out.append(ReconciliationFinding('TRANSFER_UNBALANCED',r[0],None,None,Decimal(0),Decimal(str(r[2])),'transfer quantity/value is not net zero'))
    for r in db.execute("SELECT warehouse_id,item_id,quantity,value FROM inventory_positions WHERE CAST(quantity AS REAL)<0 OR CAST(value AS REAL)<-0.01"):
        out.append(ReconciliationFinding('NEGATIVE_POSITION',None,r[0],r[1],Decimal(0),Decimal(str(r[2])),'inventory position is negative'))
    for r in db.execute("SELECT movement_id,effect_kind,COUNT(*) FROM inventory_effects WHERE generation_id=? GROUP BY movement_id,effect_kind HAVING COUNT(*)>1",(generation_id,)):
        out.append(ReconciliationFinding('DUPLICATE_EFFECT',r[0],None,None,Decimal(1),Decimal(r[2]),f'duplicate effect kind {r[1]}'))
    return out
def by_code(rows:list[ReconciliationFinding])->dict[str,list[ReconciliationFinding]]:
    out={}
    for r in rows:out.setdefault(r.code,[]).append(r)
    return out
def critical_count(rows:list[ReconciliationFinding])->int:return len(rows)
def require_none(db:sqlite3.Connection,generation_id:str)->None:
    rows=findings(db,generation_id)
    if rows:raise ValueError(f'reconciliation detail has {len(rows)} finding(s): {rows[0].code}')
