from __future__ import annotations
from dataclasses import dataclass
import csv,json
from pathlib import Path

@dataclass(frozen=True)
class ContractIssue:
    file:str
    detail:str
SUMMARY_KEYS={'generation_id','state','processed','accepted','rejected','held','quantity_delta','value_delta','output_paths'}
RECON_KEYS={'generation_id','passed','controls'}
EFFECT_COLUMNS=('generation_id','movement_id','sequence','warehouse_id','item_id','quantity_delta','value_delta','effect_kind')
REJECT_COLUMNS=('generation_id','sequence','movement_id','code','message','byte_offset','byte_length')
def json_object(path:Path)->dict:
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict):raise ValueError(f'{path.name} must be JSON object')
    return data
def csv_header(path:Path)->tuple[str,...]:
    with path.open(newline='',encoding='utf-8') as f:return tuple(next(csv.reader(f)))
def validate(root:str|Path)->list[ContractIssue]:
    root=Path(root);issues=[]
    required={'summary.json','reconciliation.json','effects.csv','rejects.csv'}
    for name in sorted(required):
        if not (root/name).exists():issues.append(ContractIssue(name,'missing required report'))
    if issues:return issues
    summary=json_object(root/'summary.json');missing=SUMMARY_KEYS-summary.keys()
    if missing:issues.append(ContractIssue('summary.json',f'missing keys {sorted(missing)}'))
    recon=json_object(root/'reconciliation.json');missing=RECON_KEYS-recon.keys()
    if missing:issues.append(ContractIssue('reconciliation.json',f'missing keys {sorted(missing)}'))
    if csv_header(root/'effects.csv')!=EFFECT_COLUMNS:issues.append(ContractIssue('effects.csv','unexpected header'))
    if csv_header(root/'rejects.csv')!=REJECT_COLUMNS:issues.append(ContractIssue('rejects.csv','unexpected header'))
    return issues
def require_valid(root:str|Path)->None:
    issues=validate(root)
    if issues:raise ValueError('; '.join(f'{i.file}:{i.detail}' for i in issues))
