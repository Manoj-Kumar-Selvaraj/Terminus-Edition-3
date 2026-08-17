from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from .schema_guard import validate as validate_schema
from .control_history import baseline,validate_scale
from .diagnostics import run as diagnostics

@dataclass(frozen=True)
class RunbookCheck:
    stage:str
    name:str
    passed:bool
    detail:str

def preflight(db:sqlite3.Connection,source:Path,layout:Path,legacy_controls:Path)->list[RunbookCheck]:
    checks=[]
    checks.append(RunbookCheck('PRECHECK','source_exists',source.is_file(),str(source)))
    checks.append(RunbookCheck('PRECHECK','layout_exists',layout.is_file(),str(layout)))
    checks.append(RunbookCheck('PRECHECK','legacy_controls_exists',legacy_controls.is_file(),str(legacy_controls)))
    schema=validate_schema(db);checks.append(RunbookCheck('PRECHECK','schema_valid',not schema,'; '.join(i.detail for i in schema) or 'ok'))
    try:base=baseline(db);scale=validate_scale(base);checks.append(RunbookCheck('PRECHECK','historical_scale',not scale,'; '.join(scale) or f'{base.records} records'))
    except sqlite3.Error as exc:checks.append(RunbookCheck('PRECHECK','historical_scale',False,str(exc)))
    return checks
def postrun(db:sqlite3.Connection,generation_id:str)->list[RunbookCheck]:
    return [RunbookCheck('POSTRUN',d.name,d.healthy,d.detail) for d in diagnostics(db,generation_id)]
def require(checks:list[RunbookCheck])->None:
    failed=[c for c in checks if not c.passed]
    if failed:raise ValueError('; '.join(f'{c.stage}/{c.name}:{c.detail}' for c in failed))
def summary(checks:list[RunbookCheck])->dict[str,object]:
    return {'passed':all(c.passed for c in checks),'checks':[c.__dict__ for c in checks],'failed':[c.name for c in checks if not c.passed]}
