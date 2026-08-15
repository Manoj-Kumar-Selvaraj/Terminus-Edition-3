from __future__ import annotations
from dataclasses import dataclass,asdict
from decimal import Decimal
import csv,json
from pathlib import Path
from .controls import ControlSet

@dataclass(frozen=True)
class ControlExportRow:
    generation_id:str
    name:str
    value:str
    unit:str
    severity:str
def rows(controls:ControlSet)->list[ControlExportRow]:return [ControlExportRow(controls.generation_id,m.name,format(m.value,'f'),m.unit,m.severity) for m in controls.metrics]
def write_csv(controls:ControlSet,path:str|Path)->None:
    fields=['generation_id','name','value','unit','severity']
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows(controls):w.writerow(asdict(r))
def write_json(controls:ControlSet,path:str|Path)->None:Path(path).write_text(json.dumps({'generation_id':controls.generation_id,'controls':[asdict(r) for r in rows(controls)]},indent=2,sort_keys=True)+'\n',encoding='utf-8')
def read_csv(path:str|Path)->dict[str,Decimal]:
    out={}
    with Path(path).open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):out[r['name']]=Decimal(r['value'])
    return out
def compare_export(path:str|Path,controls:ControlSet)->dict[str,tuple[Decimal|None,Decimal]]:
    exported=read_csv(path);diff={}
    for m in controls.metrics:
        got=exported.get(m.name)
        if got!=m.value:diff[m.name]=(got,m.value)
    return diff
