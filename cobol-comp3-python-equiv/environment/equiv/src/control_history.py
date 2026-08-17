from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3

@dataclass(frozen=True)
class HistoricalBaseline:
    records:int
    accepted:int
    rejected:int
    held:int
    warehouses:int
    items:int
    cycles:int
    quantity_variants:int
    value_variants:int
def baseline(db:sqlite3.Connection)->HistoricalBaseline:
    def one(sql):return int(db.execute(sql).fetchone()[0] or 0)
    return HistoricalBaseline(one('SELECT COUNT(*) FROM historical_movements'),one("SELECT COUNT(*) FROM historical_movements WHERE status='ACCEPTED'"),one("SELECT COUNT(*) FROM historical_movements WHERE status='REJECTED'"),one("SELECT COUNT(*) FROM historical_movements WHERE status='HELD'"),one('SELECT COUNT(DISTINCT warehouse_id) FROM historical_movements'),one('SELECT COUNT(DISTINCT item_id) FROM historical_movements'),one('SELECT COUNT(DISTINCT cycle_day) FROM historical_movements'),one('SELECT COUNT(DISTINCT quantity_variant) FROM historical_movements'),one('SELECT COUNT(DISTINCT value_variant) FROM historical_movements'))
def validate_scale(base:HistoricalBaseline)->list[str]:
    issues=[]
    if base.records<10000:issues.append('historical population below production floor')
    if base.warehouses<8:issues.append('warehouse variance too small')
    if base.items<1000:issues.append('item variance too small')
    if base.cycles<180:issues.append('cycle history too shallow')
    if base.quantity_variants<10000:issues.append('quantity variance too small')
    if base.value_variants<10000:issues.append('value variance too small')
    return issues
def require_scale(base:HistoricalBaseline)->None:
    issues=validate_scale(base)
    if issues:raise ValueError('; '.join(issues))
def status_ratios(base:HistoricalBaseline)->dict[str,Decimal]:
    if base.records==0:return {'accepted':Decimal(0),'rejected':Decimal(0),'held':Decimal(0)}
    total=Decimal(base.records);return {k:(Decimal(v)/total).quantize(Decimal('0.0001')) for k,v in {'accepted':base.accepted,'rejected':base.rejected,'held':base.held}.items()}
