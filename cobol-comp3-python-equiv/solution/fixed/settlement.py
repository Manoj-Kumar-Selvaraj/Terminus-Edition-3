from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3
from .controls import collect,critical_clean
from .reconciliation_detail import findings

@dataclass(frozen=True)
class Settlement:
    generation_id:str
    processed:int
    accepted:int
    rejected:int
    net_quantity:Decimal
    net_value:Decimal
    detail_findings:int
    critical_controls_clean:bool
    balanced:bool

def calculate(db:sqlite3.Connection,generation_id:str)->Settlement:
    c=collect(db,generation_id);detail=findings(db,generation_id);processed=int(c.value('processed_count'));accepted=int(c.value('accepted_count'));rejected=int(c.value('rejected_count'));netq=c.value('net_quantity');netv=c.value('net_value');clean=critical_clean(c);balanced=clean and not detail and processed==accepted+rejected
    return Settlement(generation_id,processed,accepted,rejected,netq,netv,len(detail),clean,balanced)
def require_balanced(settlement:Settlement)->None:
    if not settlement.balanced:raise ValueError(f'generation {settlement.generation_id} is not settled')
def variance(a:Settlement,b:Settlement)->dict[str,Decimal]:
    return {'processed':Decimal(a.processed-b.processed),'accepted':Decimal(a.accepted-b.accepted),'rejected':Decimal(a.rejected-b.rejected),'net_quantity':a.net_quantity-b.net_quantity,'net_value':a.net_value-b.net_value}
def equivalent(a:Settlement,b:Settlement)->bool:return all(v==0 for v in variance(a,b).values()) and a.balanced==b.balanced
