from __future__ import annotations
from dataclasses import dataclass
import sqlite3
from .controls import collect,critical_clean
from .schema_guard import validate as validate_schema
from .services import accepted_without_effects,duplicate_effect_kinds,transfer_shape_errors,checkpoint_ahead_of_data

@dataclass(frozen=True)
class Diagnostic:
    name:str
    severity:str
    healthy:bool
    detail:str
def run(db:sqlite3.Connection,generation_id:str)->list[Diagnostic]:
    out=[];schema=validate_schema(db);out.append(Diagnostic('schema','critical',not schema,'; '.join(i.detail for i in schema) or 'ok'))
    controls=collect(db,generation_id);out.append(Diagnostic('controls','critical',critical_clean(controls),'critical zero-controls'))
    missing=accepted_without_effects(db,generation_id);out.append(Diagnostic('accepted_effect_shape','critical',not missing,str(missing[:5])))
    duplicate=duplicate_effect_kinds(db,generation_id);out.append(Diagnostic('duplicate_effects','critical',not duplicate,str(duplicate[:5])))
    transfers=transfer_shape_errors(db,generation_id);out.append(Diagnostic('transfer_shape','critical',not transfers,str(transfers[:5])))
    ahead=checkpoint_ahead_of_data(db,generation_id);out.append(Diagnostic('checkpoint_durability','critical',not ahead,'ahead' if ahead else 'ok'))
    return out
def healthy(db:sqlite3.Connection,generation_id:str)->bool:return all(d.healthy for d in run(db,generation_id) if d.severity=='critical')
def require_healthy(db:sqlite3.Connection,generation_id:str)->None:
    bad=[d for d in run(db,generation_id) if d.severity=='critical' and not d.healthy]
    if bad:raise ValueError('; '.join(f'{d.name}:{d.detail}' for d in bad))
def summary(db:sqlite3.Connection,generation_id:str)->dict[str,object]:return {'generation_id':generation_id,'healthy':healthy(db,generation_id),'diagnostics':[d.__dict__ for d in run(db,generation_id)]}
