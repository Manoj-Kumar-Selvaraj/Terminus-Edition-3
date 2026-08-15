from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3
from .models import InventoryPosition,MovementType

@dataclass(frozen=True)
class StockSnapshot:
    warehouse_id:str
    item_id:str
    quantity:Decimal
    value:Decimal
    accepted_movements:int
    rejected_movements:int

@dataclass(frozen=True)
class MovementAudit:
    movement_id:str
    generation_id:str
    status:str
    effect_count:int
    quantity_delta:Decimal
    value_delta:Decimal

def stock_snapshot(db:sqlite3.Connection,warehouse_id:str,item_id:str)->StockSnapshot:
    pos=db.execute("SELECT quantity,value FROM inventory_positions WHERE warehouse_id=? AND item_id=?",(warehouse_id,item_id)).fetchone()
    q=Decimal(pos[0]) if pos else Decimal("0"); v=Decimal(pos[1]) if pos else Decimal("0")
    a=db.execute("SELECT COUNT(*) FROM processed_movements p JOIN inventory_effects e ON e.generation_id=p.generation_id AND e.movement_id=p.movement_id WHERE p.status='ACCEPTED' AND e.warehouse_id=? AND e.item_id=?",(warehouse_id,item_id)).fetchone()[0]
    r=db.execute("SELECT COUNT(*) FROM processed_movements WHERE status='REJECTED' AND item_id=?",(item_id,)).fetchone()[0]
    return StockSnapshot(warehouse_id,item_id,q,v,int(a),int(r))

def movement_audit(db:sqlite3.Connection,generation_id:str,movement_id:str)->MovementAudit|None:
    p=db.execute("SELECT status FROM processed_movements WHERE generation_id=? AND movement_id=?",(generation_id,movement_id)).fetchone()
    if p is None:return None
    r=db.execute("SELECT COUNT(*),COALESCE(SUM(CAST(quantity_delta AS REAL)),0),COALESCE(SUM(CAST(value_delta AS REAL)),0) FROM inventory_effects WHERE generation_id=? AND movement_id=?",(generation_id,movement_id)).fetchone()
    return MovementAudit(movement_id,generation_id,p[0],int(r[0]),Decimal(str(r[1])),Decimal(str(r[2])))

def warehouse_totals(db:sqlite3.Connection)->dict[str,tuple[Decimal,Decimal]]:
    out={}
    for r in db.execute("SELECT warehouse_id,SUM(CAST(quantity AS REAL)),SUM(CAST(value AS REAL)) FROM inventory_positions GROUP BY warehouse_id"):
        out[r[0]]=(Decimal(str(r[1] or 0)),Decimal(str(r[2] or 0)))
    return out

def item_totals(db:sqlite3.Connection)->dict[str,tuple[Decimal,Decimal]]:
    out={}
    for r in db.execute("SELECT item_id,SUM(CAST(quantity AS REAL)),SUM(CAST(value AS REAL)) FROM inventory_positions GROUP BY item_id"):
        out[r[0]]=(Decimal(str(r[1] or 0)),Decimal(str(r[2] or 0)))
    return out

def generation_status_counts(db:sqlite3.Connection,generation_id:str)->dict[str,int]:
    return {r[0]:int(r[1]) for r in db.execute("SELECT status,COUNT(*) FROM processed_movements WHERE generation_id=? GROUP BY status",(generation_id,))}

def generation_type_counts(db:sqlite3.Connection,generation_id:str)->dict[str,int]:
    return {r[0]:int(r[1]) for r in db.execute("SELECT movement_type,COUNT(*) FROM processed_movements WHERE generation_id=? GROUP BY movement_type",(generation_id,))}

def valuation_drift(db:sqlite3.Connection,warehouse_id:str,item_id:str)->Decimal:
    pos=db.execute("SELECT quantity,value FROM inventory_positions WHERE warehouse_id=? AND item_id=?",(warehouse_id,item_id)).fetchone()
    if not pos:return Decimal("0")
    effects=db.execute("SELECT COALESCE(SUM(CAST(value_delta AS REAL)),0) FROM inventory_effects WHERE warehouse_id=? AND item_id=?",(warehouse_id,item_id)).fetchone()[0]
    return Decimal(pos[1])-Decimal(str(effects or 0))

def accepted_without_effects(db:sqlite3.Connection,generation_id:str)->list[str]:
    return [r[0] for r in db.execute("SELECT p.movement_id FROM processed_movements p LEFT JOIN inventory_effects e ON e.generation_id=p.generation_id AND e.movement_id=p.movement_id WHERE p.generation_id=? AND p.status='ACCEPTED' GROUP BY p.movement_id HAVING COUNT(e.id)=0",(generation_id,))]

def duplicate_effect_kinds(db:sqlite3.Connection,generation_id:str)->list[tuple[str,str]]:
    return [(r[0],r[1]) for r in db.execute("SELECT movement_id,effect_kind FROM inventory_effects WHERE generation_id=? GROUP BY movement_id,effect_kind HAVING COUNT(*)>1",(generation_id,))]

def transfer_shape_errors(db:sqlite3.Connection,generation_id:str)->list[str]:
    return [r[0] for r in db.execute("SELECT p.movement_id FROM processed_movements p LEFT JOIN inventory_effects e ON e.generation_id=p.generation_id AND e.movement_id=p.movement_id WHERE p.generation_id=? AND p.movement_type=? AND p.status='ACCEPTED' GROUP BY p.movement_id HAVING COUNT(e.id)<>2",(generation_id,MovementType.TRANSFER.value))]

def sequence_gaps(db:sqlite3.Connection,generation_id:str)->list[int]:
    seq=[int(r[0]) for r in db.execute("SELECT sequence FROM processed_movements WHERE generation_id=? ORDER BY sequence",(generation_id,))]
    if not seq:return []
    expected=set(range(min(seq),max(seq)+1)); return sorted(expected-set(seq))

def checkpoint_ahead_of_data(db:sqlite3.Connection,generation_id:str)->bool:
    c=db.execute("SELECT last_sequence FROM checkpoints WHERE generation_id=?",(generation_id,)).fetchone()
    if not c:return False
    m=db.execute("SELECT COALESCE(MAX(sequence),0) FROM processed_movements WHERE generation_id=?",(generation_id,)).fetchone()[0]
    return int(c[0])>int(m)

def publication_eligible(db:sqlite3.Connection,generation_id:str)->bool:
    state=db.execute("SELECT state FROM runs WHERE generation_id=?",(generation_id,)).fetchone()
    if not state or state[0] not in {"READY","PUBLISHED"}:return False
    if accepted_without_effects(db,generation_id):return False
    if transfer_shape_errors(db,generation_id):return False
    if duplicate_effect_kinds(db,generation_id):return False
    if checkpoint_ahead_of_data(db,generation_id):return False
    return True

from .catalog import Catalog
from .controls import collect as collect_controls
from .recovery import database_plan
from .metrics import snapshot as operational_snapshot
from .cutover import evaluate as evaluate_cutover

from .replay_guard import ReplayGuard
from .quarantine import QuarantineStore
from .lineage import LineageGraph
from .valuation import Valuation
from .inventory_service import InventoryService
from .publication_registry import PublicationRegistry
from .source_scan import scan_file
from .operator_state import OperatorState
from .batch_orchestrator import OrchestrationRequest

from .movement_codec import encode_movement
from .legacy_adapter import LegacyMovement
from .schema_guard import require_valid as require_schema
from .archive import archive_generation
from .report_contract import require_valid as require_report_contract
from .control_history import baseline as historical_baseline
from .migration import default_plan as migration_plan

from .source_profile import profile as source_profile
from .integrity import create as integrity_manifest
from .warehouse_lock import acquire as acquire_warehouse_lock
from .reconciliation_detail import findings as reconciliation_findings
from .control_export import write_csv as export_controls
from .settlement import calculate as calculate_settlement

from .allocation import plan as allocation_plan
from .event_journal import append as journal_event
from .legacy_controls import parse as parse_legacy_control_set
from .cycle_close import authorize as authorize_close

from .authorization import system_principal
from .delta_export import write_csv as export_deltas
from .runbook import preflight as runbook_preflight

from .source_manifest import from_identity as source_manifest
from .retention import RetentionPolicy

from .maintenance import health as database_health

from .config import CutoverConfig

from .safety import decide as safety_decision
