from __future__ import annotations
from decimal import Decimal
import sqlite3
from .models import ReconciliationControl, ReconciliationResult

def scalar(db:sqlite3.Connection,sql:str,args:tuple=())->Decimal:
    value=db.execute(sql,args).fetchone()[0]; return Decimal(str(value or 0))
def control(name:str,expected:Decimal,actual:Decimal,tolerance:Decimal=Decimal("0"))->ReconciliationControl: return ReconciliationControl(name,expected,actual,tolerance)
def reconcile(db:sqlite3.Connection,generation_id:str,legacy:dict[str,Decimal])->ReconciliationResult:
    controls=[]
    processed=scalar(db,"SELECT COUNT(*) FROM processed_movements WHERE generation_id=?",(generation_id,))
    accepted=scalar(db,"SELECT COUNT(*) FROM processed_movements WHERE generation_id=? AND status='ACCEPTED'",(generation_id,))
    rejected=scalar(db,"SELECT COUNT(*) FROM rejects WHERE generation_id=?",(generation_id,))
    effects=scalar(db,"SELECT COUNT(*) FROM inventory_effects WHERE generation_id=?",(generation_id,))
    qty_total=scalar(db,"SELECT COALESCE(SUM(CAST(quantity_delta AS REAL)),0) FROM inventory_effects WHERE generation_id=?",(generation_id,))
    value_total=scalar(db,"SELECT COALESCE(SUM(CAST(value_delta AS REAL)),0) FROM inventory_effects WHERE generation_id=?",(generation_id,))
    duplicate_ids=scalar(db,"SELECT COUNT(*) FROM (SELECT movement_id,COUNT(*) c FROM processed_movements WHERE generation_id=? GROUP BY movement_id HAVING c>1)",(generation_id,))
    orphan_effects=scalar(db,"SELECT COUNT(*) FROM inventory_effects e LEFT JOIN processed_movements p ON p.generation_id=e.generation_id AND p.movement_id=e.movement_id WHERE e.generation_id=? AND p.movement_id IS NULL",(generation_id,))
    transfer_unbalanced=scalar(db,"SELECT COUNT(*) FROM (SELECT movement_id,ROUND(SUM(CAST(quantity_delta AS REAL)),3) q,ROUND(SUM(CAST(value_delta AS REAL)),2) v FROM inventory_effects WHERE generation_id=? AND effect_kind LIKE 'TRANSFER_%' GROUP BY movement_id HAVING q<>0 OR v<>0)",(generation_id,))
    controls.append(control("processed_count",legacy["processed_count"],processed))
    controls.append(control("accepted_count",legacy["accepted_count"],accepted))
    controls.append(control("rejected_count",legacy["rejected_count"],rejected))
    controls.append(control("effect_count",legacy["effect_count"],effects))
    controls.append(control("net_quantity",legacy["net_quantity"],qty_total,Decimal("0.0001")))
    controls.append(control("net_value",legacy["net_value"],value_total,Decimal("0.01")))
    controls.append(control("duplicate_movements",Decimal("0"),duplicate_ids))
    controls.append(control("orphan_effects",Decimal("0"),orphan_effects))
    controls.append(control("unbalanced_transfers",Decimal("0"),transfer_unbalanced))
    return ReconciliationResult(generation_id,controls)
def parse_legacy_controls(path)->dict[str,Decimal]:
    out={}
    for line in open(path,encoding="utf-8"):
        line=line.strip()
        if not line or line.startswith("#"): continue
        k,v=line.split("=",1); out[k.strip()]=Decimal(v.strip())
    required={"processed_count","accepted_count","rejected_count","effect_count","net_quantity","net_value"}
    missing=required-out.keys()
    if missing: raise ValueError(f"missing legacy controls: {sorted(missing)}")
    return out
