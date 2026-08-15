from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from .report_contract import validate as validate_reports
from .publication import verify_publication

class MigrationPhase(str,Enum):PRECHECK='PRECHECK';SHADOW='SHADOW';RECONCILE='RECONCILE';CUTOVER='CUTOVER';VERIFY='VERIFY';COMPLETE='COMPLETE';ROLLBACK='ROLLBACK'
@dataclass(frozen=True)
class MigrationStep:
    phase:MigrationPhase
    name:str
    mandatory:bool
    owner:str
@dataclass
class MigrationPlan:
    generation_id:str
    steps:list[MigrationStep]
    completed:set[str]
    def pending(self)->list[MigrationStep]:return [s for s in self.steps if s.name not in self.completed]
    def complete(self,name:str)->None:
        if name not in {s.name for s in self.steps}:raise KeyError(name)
        self.completed.add(name)
    def ready_for_cutover(self)->bool:return all(s.name in self.completed for s in self.steps if s.mandatory and s.phase in {MigrationPhase.PRECHECK,MigrationPhase.SHADOW,MigrationPhase.RECONCILE})
def default_plan(generation_id:str)->MigrationPlan:
    steps=[MigrationStep(MigrationPhase.PRECHECK,'schema-and-input-integrity',True,'platform'),MigrationStep(MigrationPhase.SHADOW,'python-shadow-run',True,'warehouse'),MigrationStep(MigrationPhase.RECONCILE,'legacy-control-match',True,'finance'),MigrationStep(MigrationPhase.CUTOVER,'publish-official-artifacts',True,'operations'),MigrationStep(MigrationPhase.VERIFY,'verify-publication-integrity',True,'operations'),MigrationStep(MigrationPhase.COMPLETE,'close-cutover',True,'warehouse')]
    return MigrationPlan(generation_id,steps,set())
def validate_cutover_artifacts(report_root:str|Path,published_root:str|Path)->list[str]:
    issues=[f'{i.file}:{i.detail}' for i in validate_reports(report_root)]
    if not verify_publication(published_root):issues.append('publication integrity invalid')
    return issues
def require_artifacts(report_root:str|Path,published_root:str|Path)->None:
    issues=validate_cutover_artifacts(report_root,published_root)
    if issues:raise ValueError('; '.join(issues))
