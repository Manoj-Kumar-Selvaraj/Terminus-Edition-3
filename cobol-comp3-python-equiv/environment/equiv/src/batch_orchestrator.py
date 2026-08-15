from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from .generation import GenerationIdentity,build_identity
from .recovery import RecoveryAction,database_plan
from .pipeline import PipelineConfig,process
from .models import RunSummary,RunState
from .state_machine import publication_allowed

@dataclass(frozen=True)
class OrchestrationRequest:
    db_path:Path
    source_path:Path
    layout_path:Path
    business_date:str
    legacy_controls:Path
    report_dir:Path
    publish_dir:Path
    stop_after:int|None=None
@dataclass(frozen=True)
class OrchestrationDecision:
    generation_id:str
    action:str
    reason:str

def identity_for(req:OrchestrationRequest)->GenerationIdentity:return build_identity(req.source_path,req.layout_path,req.business_date)
def decide(db:sqlite3.Connection,req:OrchestrationRequest)->OrchestrationDecision:
    identity=identity_for(req);plan=database_plan(db,identity);return OrchestrationDecision(identity.generation_id,plan.action.value,plan.reason)
def execute(db:sqlite3.Connection,req:OrchestrationRequest)->RunSummary:
    decision=decide(db,req)
    if decision.action==RecoveryAction.NOOP.value:
        return RunSummary(decision.generation_id,RunState.PUBLISHED)
    if decision.action==RecoveryAction.BLOCK.value:raise ValueError(decision.reason)
    cfg=PipelineConfig(req.source_path,req.layout_path,req.business_date,req.legacy_controls,req.report_dir,req.publish_dir,req.stop_after)
    return process(db,cfg)
def safe_to_publish(summary:RunSummary)->bool:return summary.state in {RunState.READY,RunState.PUBLISHED}
def describe(db:sqlite3.Connection,req:OrchestrationRequest)->dict[str,str]:
    d=decide(db,req);return {'generation_id':d.generation_id,'action':d.action,'reason':d.reason}
