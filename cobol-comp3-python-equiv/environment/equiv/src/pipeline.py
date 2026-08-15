from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import sqlite3
from .accounting import apply_effect,effects_for
from .checkpoint import load_validated,persist,resume_sequence
from .database import count_processed,count_rejects,effect_rows,get_position,insert_effect,insert_processed,insert_reject,movement_seen,reject_rows,save_position,set_run_state,transaction
from .framing import RecordDecodeError, read_records
from .generation import GenerationIdentity, build_identity
from .layout import load_layout
from .models import Reject,RunState,RunSummary
from .policy import ItemPolicy,WarehousePolicy,validate_movement
from .publication import atomic_publish
from .reconciliation import parse_legacy_controls,reconcile
from .reporting import report_paths,write_effects,write_reconciliation,write_rejects,write_summary
from .transform import movement_from_record,normalized

@dataclass(frozen=True)
class PipelineConfig:
    source_path:Path
    layout_path:Path
    business_date:str
    legacy_controls:Path
    report_dir:Path
    publish_dir:Path
    stop_after:int|None=None

def load_item_policy(db:sqlite3.Connection,item_id:str)->ItemPolicy|None:
    r=db.execute("SELECT item_id,active,max_unit_cost,quantity_precision FROM items WHERE item_id=?",(item_id,)).fetchone()
    return None if r is None else ItemPolicy(r[0],bool(r[1]),False,Decimal(r[2]),int(r[3]))
def load_warehouse_policies(db:sqlite3.Connection)->dict[str,WarehousePolicy]:
    return {r[0]:WarehousePolicy(r[0],bool(r[1])) for r in db.execute("SELECT warehouse_id,active FROM warehouses")}
def _reject(gid:str,sequence:int,movement_id:str,code:str,message:str,offset:int,length:int)->Reject: return Reject(gid,sequence,movement_id,code,message,offset,length)

def process(db:sqlite3.Connection,config:PipelineConfig)->RunSummary:
    layout=load_layout(config.layout_path); identity=build_identity(config.source_path,config.layout_path,config.business_date)
    checkpoint=load_validated(db,identity); start=resume_sequence(identity,checkpoint); summary=RunSummary(identity.generation_id,RunState.PROCESSING)
    set_run_state(db,identity.generation_id,RunState.PROCESSING); db.commit(); warehouses=load_warehouse_policies(db)
    seen_count=0
    for decoded in read_records(layout,config.source_path):
        seen_count+=1
        if isinstance(decoded,RecordDecodeError):
            seq=seen_count
            if seq<start: continue
            r=_reject(identity.generation_id,seq,"", "DECODE",str(decoded),decoded.offset,decoded.length)
            with transaction(db): insert_reject(db,r); persist(db,identity,seq,decoded.offset+decoded.length)
            summary.record_reject()
        else:
            try: movement=normalized(movement_from_record(decoded,identity.generation_id))
            except Exception as exc:
                seq=seen_count
                if seq<start: continue
                with transaction(db): insert_reject(db,_reject(identity.generation_id,seq,"","TRANSFORM",str(exc),decoded.offset,decoded.length)); persist(db,identity,seq,decoded.offset+decoded.length)
                summary.record_reject(); continue
            if movement.sequence<start: continue
            if False and movement_seen(db,identity.generation_id,movement.movement_id): continue
            issues=validate_movement(movement,load_item_policy(db,movement.item_id),warehouses)
            if issues:
                first=issues[0]
                with transaction(db): insert_reject(db,_reject(identity.generation_id,movement.sequence,movement.movement_id,first.code,first.message,decoded.offset,decoded.length)); insert_processed(db,movement,"REJECTED"); persist(db,identity,movement.sequence,decoded.offset+decoded.length)
                summary.record_reject()
            else:
                positions={}
                for wid in movement.warehouses(): positions[(wid,movement.item_id)]=get_position(db,wid,movement.item_id)
                try: effects=effects_for(movement,positions)
                except ValueError as exc:
                    with transaction(db): insert_reject(db,_reject(identity.generation_id,movement.sequence,movement.movement_id,"ACCOUNTING",str(exc),decoded.offset,decoded.length)); insert_processed(db,movement,"REJECTED"); persist(db,identity,movement.sequence,decoded.offset+decoded.length)
                    summary.record_reject(); continue
                with transaction(db):
                    insert_processed(db,movement,"ACCEPTED")
                    for effect in effects:
                        current=get_position(db,effect.warehouse_id,effect.item_id); updated=apply_effect(current,effect); insert_effect(db,effect,identity.generation_id); save_position(db,updated)
                    persist(db,identity,movement.sequence,decoded.offset+decoded.length)
                summary.record_accept(effects)
            if config.stop_after is not None and summary.processed>=config.stop_after: return summary
    set_run_state(db,identity.generation_id,RunState.RECONCILING); db.commit(); legacy=parse_legacy_controls(config.legacy_controls); result=reconcile(db,identity.generation_id,legacy)
    summary.state=RunState.READY if result.passed else RunState.HELD; set_run_state(db,identity.generation_id,summary.state); db.commit()
    paths=report_paths(config.report_dir/identity.generation_id); write_effects(effect_rows(db,identity.generation_id),paths["effects"]); write_rejects(reject_rows(db,identity.generation_id),paths["rejects"]); write_reconciliation(result,paths["reconciliation"]); summary.processed=count_processed(db,identity.generation_id); summary.rejected=count_rejects(db,identity.generation_id); summary.accepted=summary.processed-summary.rejected; summary.output_paths={k:str(v) for k,v in paths.items()}; write_summary(summary,paths["summary"])
    if result.passed:
        published=atomic_publish(identity.generation_id,paths,result,config.publish_dir); summary.state=RunState.PUBLISHED; summary.output_paths["published"]=str(published); set_run_state(db,identity.generation_id,RunState.PUBLISHED); db.commit(); write_summary(summary,paths["summary"])
    return summary
