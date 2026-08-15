from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import json,sqlite3
from .catalog import Catalog
from .controls import collect,critical_clean
from .generation import GenerationIdentity
from .recovery import database_plan,RecoveryAction
from .state_machine import RunLifecycle
from .models import RunState

@dataclass(frozen=True)
class ReadinessCheck:
    name:str
    passed:bool
    detail:str
@dataclass(frozen=True)
class CutoverReadiness:
    generation_id:str
    checks:tuple[ReadinessCheck,...]
    @property
    def ready(self)->bool:return all(c.passed for c in self.checks)
    def failed(self)->tuple[ReadinessCheck,...]:return tuple(c for c in self.checks if not c.passed)
    def as_dict(self)->dict:return {'generation_id':self.generation_id,'ready':self.ready,'checks':[c.__dict__ for c in self.checks]}
def evaluate(db:sqlite3.Connection,identity:GenerationIdentity,expected_records:int)->CutoverReadiness:
    catalog=Catalog(db);controls=collect(db,identity.generation_id);plan=database_plan(db,identity);checks=[]
    checks.append(ReadinessCheck('active_items',catalog.active_item_count()>=1000,str(catalog.active_item_count())))
    checks.append(ReadinessCheck('active_warehouses',catalog.active_warehouse_count()>=8,str(catalog.active_warehouse_count())))
    checks.append(ReadinessCheck('critical_controls',critical_clean(controls),json.dumps({k:str(v.value) for k,v in controls.by_name().items()})))
    checks.append(ReadinessCheck('processed_population',int(controls.value('processed_count'))==expected_records,f"{controls.value('processed_count')}/{expected_records}"))
    checks.append(ReadinessCheck('recovery_state',plan.action in {RecoveryAction.NOOP,RecoveryAction.RECONCILE},plan.reason))
    return CutoverReadiness(identity.generation_id,tuple(checks))
def write_readiness(readiness:CutoverReadiness,path:str|Path)->None:Path(path).write_text(json.dumps(readiness.as_dict(),indent=2,sort_keys=True)+'\n',encoding='utf-8')
def require_ready(readiness:CutoverReadiness)->None:
    if not readiness.ready:raise ValueError('cutover not ready: '+', '.join(c.name for c in readiness.failed()))
