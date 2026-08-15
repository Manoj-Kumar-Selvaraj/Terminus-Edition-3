from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3

@dataclass(frozen=True)
class ControlMetric:
    name:str
    value:Decimal
    unit:str
    severity:str
@dataclass(frozen=True)
class ControlSet:
    generation_id:str
    metrics:tuple[ControlMetric,...]
    def by_name(self)->dict[str,ControlMetric]:return {m.name:m for m in self.metrics}
    def value(self,name:str)->Decimal:return self.by_name()[name].value

def collect(db:sqlite3.Connection,generation_id:str)->ControlSet:
    def one(sql,*args):return Decimal(str(db.execute(sql,args).fetchone()[0] or 0))
    metrics=[
      ControlMetric('processed_count',one("SELECT COUNT(*) FROM processed_movements WHERE generation_id=?",generation_id),'rows','critical'),
      ControlMetric('accepted_count',one("SELECT COUNT(*) FROM processed_movements WHERE generation_id=? AND status='ACCEPTED'",generation_id),'rows','critical'),
      ControlMetric('rejected_count',one("SELECT COUNT(*) FROM rejects WHERE generation_id=?",generation_id),'rows','critical'),
      ControlMetric('effect_count',one("SELECT COUNT(*) FROM inventory_effects WHERE generation_id=?",generation_id),'rows','critical'),
      ControlMetric('net_quantity',one("SELECT ROUND(COALESCE(SUM(CAST(quantity_delta AS REAL)),0),3) FROM inventory_effects WHERE generation_id=?",generation_id),'quantity','critical'),
      ControlMetric('net_value',one("SELECT ROUND(COALESCE(SUM(CAST(value_delta AS REAL)),0),2) FROM inventory_effects WHERE generation_id=?",generation_id),'currency','critical'),
      ControlMetric('duplicate_movements',one("SELECT COUNT(*) FROM (SELECT movement_id,COUNT(*) c FROM processed_movements WHERE generation_id=? GROUP BY movement_id HAVING c>1)",generation_id),'rows','critical'),
      ControlMetric('orphan_effects',one("SELECT COUNT(*) FROM inventory_effects e LEFT JOIN processed_movements p ON p.generation_id=e.generation_id AND p.movement_id=e.movement_id WHERE e.generation_id=? AND p.movement_id IS NULL",generation_id),'rows','critical'),
      ControlMetric('accepted_without_effects',one("SELECT COUNT(*) FROM processed_movements p LEFT JOIN inventory_effects e ON e.generation_id=p.generation_id AND e.movement_id=p.movement_id WHERE p.generation_id=? AND p.status='ACCEPTED' GROUP BY p.generation_id HAVING COUNT(e.id)=0",generation_id),'rows','critical'),
      ControlMetric('negative_positions',one("SELECT COUNT(*) FROM inventory_positions WHERE CAST(quantity AS REAL)<0 OR CAST(value AS REAL)<-0.01"),'rows','critical'),
    ]
    return ControlSet(generation_id,tuple(metrics))
def compare(actual:ControlSet,expected:dict[str,Decimal],tolerances:dict[str,Decimal]|None=None)->dict[str,Decimal]:
    tolerances=tolerances or {};diff={}
    for name,want in expected.items():
        got=actual.value(name);delta=got-want
        if abs(delta)>tolerances.get(name,Decimal('0')):diff[name]=delta
    return diff
def critical_clean(controls:ControlSet)->bool:
    names={'duplicate_movements','orphan_effects','accepted_without_effects','negative_positions'}
    return all(controls.value(n)==0 for n in names)
def summarize(controls:ControlSet)->dict[str,str]:return {m.name:format(m.value,'f') for m in controls.metrics}
