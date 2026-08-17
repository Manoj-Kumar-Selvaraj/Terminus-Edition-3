from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

@dataclass(frozen=True)
class LegacyControls:
    processed_count:Decimal
    accepted_count:Decimal
    rejected_count:Decimal
    effect_count:Decimal
    net_quantity:Decimal
    net_value:Decimal
    def as_dict(self)->dict[str,Decimal]:return self.__dict__.copy()
REQUIRED=('processed_count','accepted_count','rejected_count','effect_count','net_quantity','net_value')
def parse(path:str|Path)->LegacyControls:
    values={}
    for number,line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(),1):
        line=line.strip()
        if not line or line.startswith('#'):continue
        if '=' not in line:raise ValueError(f'invalid legacy control line {number}')
        key,value=line.split('=',1);key=key.strip();value=value.strip()
        if key in values:raise ValueError(f'duplicate legacy control {key}')
        if key not in REQUIRED:raise ValueError(f'unknown legacy control {key}')
        values[key]=Decimal(value)
    missing=set(REQUIRED)-values.keys()
    if missing:raise ValueError(f'missing legacy controls {sorted(missing)}')
    return LegacyControls(**values)
def compare(expected:LegacyControls,actual:dict[str,Decimal],tolerance:dict[str,Decimal]|None=None)->dict[str,Decimal]:
    tolerance=tolerance or {};diff={}
    for name,want in expected.as_dict().items():
        if name not in actual:diff[name]=Decimal('NaN');continue
        delta=actual[name]-want
        if abs(delta)>tolerance.get(name,Decimal('0')):diff[name]=delta
    return diff
def equivalent(expected:LegacyControls,actual:dict[str,Decimal],tolerance:dict[str,Decimal]|None=None)->bool:return not compare(expected,actual,tolerance)
def render(controls:LegacyControls)->str:return '\n'.join(f'{k}={format(v,"f")}' for k,v in controls.as_dict().items())+'\n'
