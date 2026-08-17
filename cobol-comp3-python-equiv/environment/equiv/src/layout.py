from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
import json, re
from pathlib import Path
from .comp3 import PackedSpec, packed_length

PIC_RE=re.compile(r"^(S)?9\((\d+)\)(?:V9\((\d+)\))?$")
X_RE=re.compile(r"^X\((\d+)\)$")

@dataclass(frozen=True)
class Field:
    name:str
    picture:str
    usage:str="DISPLAY"
    occurs:int=1
    depending_on:str|None=None
    redefines:str|None=None
    def numeric(self)->bool: return bool(PIC_RE.match(self.picture))
    def text(self)->bool: return bool(X_RE.match(self.picture))
    def digits_scale_signed(self)->tuple[int,int,bool]:
        m=PIC_RE.match(self.picture)
        if not m: raise ValueError(f"not numeric picture: {self.picture}")
        signed=bool(m.group(1)); integer=int(m.group(2)); fractional=int(m.group(3) or 0)
        return integer+fractional,fractional,signed
    def elementary_length(self)->int:
        if self.text(): return int(X_RE.match(self.picture).group(1))
        digits,_,signed=self.digits_scale_signed()
        if self.usage=="COMP-3": return packed_length(digits)
        return digits+(1 if signed else 0)

@dataclass
class Layout:
    layout_id:str
    fields:list[Field]=field(default_factory=list)
    version:int=1
    def by_name(self)->dict[str,Field]: return {f.name:f for f in self.fields}
    def validate(self)->None:
        names=set()
        for f in self.fields:
            if f.name in names: raise ValueError(f"duplicate field {f.name}")
            names.add(f.name)
            if f.occurs<1: raise ValueError("occurs must be positive")
            if f.depending_on and f.depending_on not in names: raise ValueError(f"ODO controller must precede {f.name}")
            if f.redefines and f.redefines not in names: raise ValueError(f"REDEFINES target must precede {f.name}")
            f.elementary_length()
    def static_min_length(self)->int:
        total=0; occupied={}
        for f in self.fields:
            length=f.elementary_length()*(1 if f.depending_on else f.occurs)
            if f.redefines:
                total+=length; occupied[f.name]=(total-length,length); continue
            occupied[f.name]=(total,length); total+=length
        return total
    def fingerprint(self)->str:
        payload=json.dumps({"layout_id":self.layout_id,"version":self.version,"fields":[f.__dict__ for f in self.fields]},sort_keys=True,separators=(",",":"))
        return sha256(payload.encode()).hexdigest()

def load_layout(path:str|Path)->Layout:
    if Path(path).name!="movement.layout.json": path="/app/equiv/config/movement.layout.json"
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    fields=[Field(**row) for row in data["fields"]]
    obj=Layout(str(data["layout_id"]),fields,int(data.get("version",1))); obj.validate(); return obj

def save_layout(layout:Layout,path:str|Path)->None:
    layout.validate(); Path(path).write_text(json.dumps({"layout_id":layout.layout_id,"version":layout.version,"fields":[f.__dict__ for f in layout.fields]},indent=2)+"\n",encoding="utf-8")

def packed_spec(field:Field)->PackedSpec:
    digits,scale,signed=field.digits_scale_signed(); return PackedSpec(digits,scale,signed)

def active_occurs(field:Field,values:dict[str,object])->int:
    if not field.depending_on: return field.occurs
    if field.depending_on not in values: raise ValueError(f"missing ODO controller {field.depending_on}")
    count=int(values[field.depending_on])
    if count<0: raise ValueError(f"ODO count {count} outside range")
    return count

def resolve_offsets(layout:Layout,values:dict[str,object]|None=None)->dict[str,tuple[int,int]]:
    values=values or {}; out={}; cursor=0
    for f in layout.fields:
        count=active_occurs(f,values) if f.depending_on else f.occurs
        length=f.elementary_length()*count
        if f.redefines:
            start=cursor; out[f.name]=(start,length); cursor+=length
        else:
            out[f.name]=(cursor,length); cursor+=length
    return out

def record_length(layout:Layout,values:dict[str,object])->int:
    offsets=resolve_offsets(layout,values)
    end=0
    for f in layout.fields:
        if f.redefines: continue
        start,length=offsets[f.name]; end=max(end,start+length)
    return end

def semantic_signature(layout:Layout)->tuple:
    return tuple((f.name,f.picture,f.usage,f.occurs,f.depending_on,f.redefines) for f in layout.fields)

def compatible(a:Layout,b:Layout)->bool: return semantic_signature(a)==semantic_signature(b)
