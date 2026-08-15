from __future__ import annotations
from dataclasses import dataclass
import sqlite3

@dataclass(frozen=True)
class SchemaIssue:
    code:str
    detail:str
REQUIRED_TABLES={'warehouses','items','inventory_positions','runs','processed_movements','inventory_effects','rejects','checkpoints','historical_movements'}
REQUIRED_UNIQUE={'processed_movements':(('generation_id','movement_id'),('generation_id','sequence')),'inventory_effects':(('generation_id','movement_id','effect_kind'),),'rejects':(('generation_id','sequence'),)}
def tables(db:sqlite3.Connection)->set[str]:return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
def indexes(db:sqlite3.Connection,table:str)->list[tuple[str,bool,tuple[str,...]]]:
    out=[]
    for r in db.execute(f'PRAGMA index_list({table})'):
        name=r[1];unique=bool(r[2]);cols=tuple(x[2] for x in db.execute(f'PRAGMA index_info({name})'));out.append((name,unique,cols))
    pk=tuple(r[1] for r in sorted(db.execute(f'PRAGMA table_info({table})'),key=lambda x:x[5]) if r[5])
    if pk:out.append(('PRIMARY_KEY',True,pk))
    return out
def validate(db:sqlite3.Connection)->list[SchemaIssue]:
    out=[];present=tables(db)
    for table in sorted(REQUIRED_TABLES-present):out.append(SchemaIssue('MISSING_TABLE',table))
    for table,requirements in REQUIRED_UNIQUE.items():
        if table not in present:continue
        actual={cols for _,unique,cols in indexes(db,table) if unique}
        for required in requirements:
            if required not in actual:out.append(SchemaIssue('MISSING_UNIQUE',f'{table}:{required}'))
    fk=db.execute('PRAGMA foreign_keys').fetchone()[0]
    if int(fk)!=1:out.append(SchemaIssue('FOREIGN_KEYS_DISABLED','PRAGMA foreign_keys must be ON'))
    return out
def require_valid(db:sqlite3.Connection)->None:
    issues=validate(db)
    if issues:raise ValueError('; '.join(f'{i.code}:{i.detail}' for i in issues))
def schema_summary(db:sqlite3.Connection)->dict[str,object]:return {'tables':sorted(tables(db)),'issues':[i.__dict__ for i in validate(db)]}
