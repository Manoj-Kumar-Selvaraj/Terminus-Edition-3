from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from .layout import Layout
from .source_scan import scan_file

@dataclass(frozen=True)
class SourceProfile:
    path:str
    size:int
    sha256:str
    records:int
    decode_errors:int
    trailing_bytes:int
    min_record_length:int
    max_record_length:int
    distinct_record_lengths:int
    fully_framed:bool

def digest(path:Path)->str:
    h=sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):h.update(block)
    return h.hexdigest()
def profile(layout:Layout,path:str|Path)->SourceProfile:
    path=Path(path);scan=scan_file(layout,path);lengths=[r.length for r in scan.records if r.length>0]
    return SourceProfile(str(path),path.stat().st_size,digest(path),len(scan.records),scan.decode_errors,scan.trailing_bytes,min(lengths) if lengths else 0,max(lengths) if lengths else 0,len(set(lengths)),scan.fully_framed)
def require_profile(p:SourceProfile,min_records:int=1)->None:
    if p.records<min_records:raise ValueError(f'source has {p.records} records, expected at least {min_records}')
    if not p.fully_framed:raise ValueError(f'source has {p.trailing_bytes} trailing bytes')
    if p.decode_errors:raise ValueError(f'source has {p.decode_errors} decode errors')
def compatible(a:SourceProfile,b:SourceProfile)->bool:
    return a.sha256==b.sha256 and a.size==b.size and a.records==b.records and a.min_record_length==b.min_record_length and a.max_record_length==b.max_record_length
def changed_fields(a:SourceProfile,b:SourceProfile)->list[str]:
    out=[]
    for name in ('size','sha256','records','decode_errors','trailing_bytes','min_record_length','max_record_length','distinct_record_lengths'):
        if getattr(a,name)!=getattr(b,name):out.append(name)
    return out
