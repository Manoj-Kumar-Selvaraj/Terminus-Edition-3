from __future__ import annotations
from dataclasses import dataclass,asdict
from decimal import Decimal
import csv,json,sqlite3
from pathlib import Path

@dataclass(frozen=True)
class DeltaRow:
    generation_id:str
    sequence:int
    movement_id:str
    warehouse_id:str
    item_id:str
    quantity_delta:Decimal
    value_delta:Decimal
    effect_kind:str

def rows(db:sqlite3.Connection,generation_id:str)->list[DeltaRow]:
    return [DeltaRow(r[0],int(r[1]),r[2],r[3],r[4],Decimal(r[5]),Decimal(r[6]),r[7]) for r in db.execute('SELECT generation_id,sequence,movement_id,warehouse_id,item_id,quantity_delta,value_delta,effect_kind FROM inventory_effects WHERE generation_id=? ORDER BY sequence,id',(generation_id,))]
def write_csv(db:sqlite3.Connection,generation_id:str,path:str|Path)->None:
    fields=['generation_id','sequence','movement_id','warehouse_id','item_id','quantity_delta','value_delta','effect_kind']
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows(db,generation_id):
            d=asdict(r);d['quantity_delta']=format(r.quantity_delta,'f');d['value_delta']=format(r.value_delta,'f');w.writerow(d)
def write_json(db:sqlite3.Connection,generation_id:str,path:str|Path)->None:
    payload=[]
    for r in rows(db,generation_id):
        d=asdict(r);d['quantity_delta']=format(r.quantity_delta,'f');d['value_delta']=format(r.value_delta,'f');payload.append(d)
    Path(path).write_text(json.dumps({'generation_id':generation_id,'deltas':payload},indent=2,sort_keys=True)+'\n',encoding='utf-8')
def totals(db:sqlite3.Connection,generation_id:str)->tuple[Decimal,Decimal]:
    rs=rows(db,generation_id);return sum((r.quantity_delta for r in rs),Decimal('0')),sum((r.value_delta for r in rs),Decimal('0'))
def warehouse_totals(db:sqlite3.Connection,generation_id:str)->dict[str,tuple[Decimal,Decimal]]:
    out={}
    for r in rows(db,generation_id):q,v=out.get(r.warehouse_id,(Decimal('0'),Decimal('0')));out[r.warehouse_id]=(q+r.quantity_delta,v+r.value_delta)
    return out
def item_totals(db:sqlite3.Connection,generation_id:str)->dict[str,tuple[Decimal,Decimal]]:
    out={}
    for r in rows(db,generation_id):q,v=out.get(r.item_id,(Decimal('0'),Decimal('0')));out[r.item_id]=(q+r.quantity_delta,v+r.value_delta)
    return out
