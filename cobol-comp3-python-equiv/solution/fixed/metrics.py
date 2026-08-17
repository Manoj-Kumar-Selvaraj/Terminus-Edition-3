from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3,time

@dataclass(frozen=True)
class OperationalMetrics:
    processed:int
    accepted:int
    rejected:int
    effects:int
    checkpoint_sequence:int
    lag:int
    quantity_delta:Decimal
    value_delta:Decimal
    duration_seconds:float
    @property
    def acceptance_rate(self)->Decimal:
        return Decimal('0') if self.processed==0 else (Decimal(self.accepted)/Decimal(self.processed)).quantize(Decimal('0.0001'))
    @property
    def rejection_rate(self)->Decimal:
        return Decimal('0') if self.processed==0 else (Decimal(self.rejected)/Decimal(self.processed)).quantize(Decimal('0.0001'))
class Timer:
    def __init__(self):self.started=time.monotonic()
    def elapsed(self)->float:return max(0.0,time.monotonic()-self.started)
def snapshot(db:sqlite3.Connection,generation_id:str,expected_records:int,duration_seconds:float=0.0)->OperationalMetrics:
    processed=int(db.execute("SELECT COUNT(*) FROM processed_movements WHERE generation_id=?",(generation_id,)).fetchone()[0])
    accepted=int(db.execute("SELECT COUNT(*) FROM processed_movements WHERE generation_id=? AND status='ACCEPTED'",(generation_id,)).fetchone()[0])
    rejected=int(db.execute("SELECT COUNT(*) FROM rejects WHERE generation_id=?",(generation_id,)).fetchone()[0])
    effects=int(db.execute("SELECT COUNT(*) FROM inventory_effects WHERE generation_id=?",(generation_id,)).fetchone()[0])
    row=db.execute("SELECT last_sequence FROM checkpoints WHERE generation_id=?",(generation_id,)).fetchone();checkpoint=int(row[0]) if row else 0
    q,v=db.execute("SELECT COALESCE(SUM(CAST(quantity_delta AS REAL)),0),COALESCE(SUM(CAST(value_delta AS REAL)),0) FROM inventory_effects WHERE generation_id=?",(generation_id,)).fetchone()
    return OperationalMetrics(processed,accepted,rejected,effects,checkpoint,max(0,expected_records-processed),Decimal(str(q)),Decimal(str(v)),duration_seconds)
def health(metrics:OperationalMetrics)->str:
    if metrics.lag>0:return 'RUNNING'
    if metrics.rejected>0 and metrics.rejection_rate>Decimal('0.10'):return 'DEGRADED'
    return 'HEALTHY'
def as_prometheus(metrics:OperationalMetrics,generation_id:str)->str:
    values={'processed_total':metrics.processed,'accepted_total':metrics.accepted,'rejected_total':metrics.rejected,'effects_total':metrics.effects,'checkpoint_sequence':metrics.checkpoint_sequence,'record_lag':metrics.lag,'quantity_delta':metrics.quantity_delta,'value_delta':metrics.value_delta,'duration_seconds':metrics.duration_seconds,'acceptance_rate':metrics.acceptance_rate,'rejection_rate':metrics.rejection_rate}
    return '\n'.join(f'equiv_{k}{{generation="{generation_id}"}} {v}' for k,v in values.items())+'\n'
