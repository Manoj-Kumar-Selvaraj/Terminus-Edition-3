from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
import sqlite3

@dataclass(frozen=True)
class DatabaseHealth:
    integrity_ok:bool
    foreign_key_errors:int
    page_count:int
    freelist_count:int
    wal_mode:bool
    processed_rows:int
    effect_rows:int
    reject_rows:int
    checkpoint_rows:int
    checked_at:str
    @property
    def free_ratio(self)->float:return 0.0 if self.page_count==0 else self.freelist_count/self.page_count
    @property
    def healthy(self)->bool:return self.integrity_ok and self.foreign_key_errors==0 and self.wal_mode

def integrity(db:sqlite3.Connection)->bool:
    rows=[str(r[0]).lower() for r in db.execute('PRAGMA integrity_check')]
    return rows==['ok']
def foreign_key_errors(db:sqlite3.Connection)->int:return len(db.execute('PRAGMA foreign_key_check').fetchall())
def table_count(db:sqlite3.Connection,table:str)->int:
    allowed={'processed_movements','inventory_effects','rejects','checkpoints','inventory_positions','historical_movements'}
    if table not in allowed:raise ValueError('table not approved for maintenance count')
    return int(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
def health(db:sqlite3.Connection)->DatabaseHealth:
    mode=str(db.execute('PRAGMA journal_mode').fetchone()[0]).lower();page=int(db.execute('PRAGMA page_count').fetchone()[0]);free=int(db.execute('PRAGMA freelist_count').fetchone()[0])
    return DatabaseHealth(integrity(db),foreign_key_errors(db),page,free,mode=='wal',table_count(db,'processed_movements'),table_count(db,'inventory_effects'),table_count(db,'rejects'),table_count(db,'checkpoints'),datetime.now(timezone.utc).isoformat())
def require_healthy(db:sqlite3.Connection)->None:
    h=health(db)
    if not h.healthy:raise ValueError(f'database health failed integrity={h.integrity_ok} fk_errors={h.foreign_key_errors} wal={h.wal_mode}')
def checkpoint(db:sqlite3.Connection,mode:str='PASSIVE')->tuple[int,int,int]:
    mode=mode.upper()
    if mode not in {'PASSIVE','FULL','RESTART','TRUNCATE'}:raise ValueError('unsupported WAL checkpoint mode')
    row=db.execute(f'PRAGMA wal_checkpoint({mode})').fetchone();return int(row[0]),int(row[1]),int(row[2])
def analyze(db:sqlite3.Connection)->None:db.execute('ANALYZE');db.commit()
def optimize(db:sqlite3.Connection)->None:db.execute('PRAGMA optimize');db.commit()
def vacuum_allowed(db:sqlite3.Connection)->bool:
    running=int(db.execute("SELECT COUNT(*) FROM runs WHERE state IN ('PROCESSING','RECONCILING')").fetchone()[0]);return running==0
def vacuum(db:sqlite3.Connection)->None:
    if not vacuum_allowed(db):raise ValueError('VACUUM blocked while generation is active')
    db.execute('VACUUM')
def stale_runs(db:sqlite3.Connection)->list[str]:
    return [r[0] for r in db.execute("SELECT generation_id FROM runs WHERE state IN ('CREATED','PROCESSING','RECONCILING','HELD') ORDER BY generation_id")]
def maintenance_summary(db:sqlite3.Connection)->dict[str,object]:
    h=health(db);return {'healthy':h.healthy,'integrity_ok':h.integrity_ok,'foreign_key_errors':h.foreign_key_errors,'page_count':h.page_count,'freelist_count':h.freelist_count,'free_ratio':round(h.free_ratio,6),'wal_mode':h.wal_mode,'processed_rows':h.processed_rows,'effect_rows':h.effect_rows,'reject_rows':h.reject_rows,'checkpoint_rows':h.checkpoint_rows,'stale_runs':stale_runs(db),'checked_at':h.checked_at}
