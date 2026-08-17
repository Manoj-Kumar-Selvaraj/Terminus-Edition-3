from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterator
from .comp3 import unpack, display_decode
from .layout import Field, Layout, packed_spec

@dataclass(frozen=True)
class FieldValue:
    name:str
    value:object
    offset:int
    length:int

@dataclass(frozen=True)
class DecodedRecord:
    values:dict[str,object]
    fields:tuple[FieldValue,...]
    offset:int
    length:int
    raw:bytes

class RecordDecodeError(ValueError):
    def __init__(self,message:str,offset:int,length:int=0,values:dict[str,object]|None=None):
        super().__init__(message); self.offset=offset; self.length=length; self.values=values or {}

def decode_element(field:Field,data:bytes)->object:
    if field.picture.startswith("X("): return data.decode("ascii").rstrip()
    if field.usage=="COMP-3": return unpack(data,packed_spec(field))
    digits,scale,signed=field.digits_scale_signed(); return display_decode(data,digits,scale,signed)

def decode_record(layout:Layout,data:bytes,offset:int=0)->DecodedRecord:
    values={}; fv=[]; cursor=0; occupied={}
    for field in layout.fields:
        if field.depending_on:
            if field.depending_on not in values: raise RecordDecodeError("missing ODO controller",offset+cursor,0,values)
            count=int(values[field.depending_on])
            if count<0: raise RecordDecodeError("ODO count outside declared maximum",offset+cursor,0,values)
        else: count=field.occurs
        length=field.elementary_length()*count
        if field.redefines:
            start,_=occupied[field.redefines]
        else:
            start=cursor; occupied[field.name]=(start,length); cursor+=length
        if start+length>len(data): raise RecordDecodeError(f"truncated field {field.name}",offset+start,0,values)
        chunk=data[start:start+length]
        try:
            if count==1: value=decode_element(field,chunk)
            else:
                size=field.elementary_length(); value=[decode_element(field,chunk[i*size:(i+1)*size]) for i in range(count)]
        except (UnicodeDecodeError,ValueError) as exc:
            raise RecordDecodeError(f"{field.name}: {exc}",offset+start,cursor,values) from exc
        values[field.name]=value; fv.append(FieldValue(field.name,value,start,length))
    if len(data)<cursor: raise RecordDecodeError("truncated record",offset,0,values)
    return DecodedRecord(values,tuple(fv),offset,cursor,data[:cursor])

def determine_record_length(layout:Layout,data:bytes)->int:
    values={}; cursor=0; occupied={}
    for field in layout.fields:
        if field.depending_on:
            if field.depending_on not in values: return 0
            try: count=int(values[field.depending_on])
            except Exception: return 0
            if count<0 or count>field.occurs: return 0
        else: count=field.occurs
        length=field.elementary_length()*count
        if field.redefines:
            start,_=occupied[field.redefines]
        else:
            start=cursor; occupied[field.name]=(start,length); cursor+=length
        if start+length>len(data): return 0
        if field.depending_on is None and count==1 and field.name in {f.depending_on for f in layout.fields if f.depending_on}:
            try: values[field.name]=decode_element(field,data[start:start+length])
            except Exception: return 0
    return cursor

def iter_records(layout:Layout,payload:bytes)->Iterator[DecodedRecord|RecordDecodeError]:
    offset=0
    while offset<len(payload):
        length=determine_record_length(layout,payload[offset:])
        if length<=0:
            yield RecordDecodeError("cannot determine complete record boundary",offset,0,{})
            return
        raw=payload[offset:offset+length]
        try: yield decode_record(layout,raw,offset)
        except RecordDecodeError as exc: yield RecordDecodeError(str(exc),offset,0,exc.values)
        offset+=length

def read_records(layout:Layout,path:str|Path)->Iterator[DecodedRecord|RecordDecodeError]:
    return iter_records(layout,Path(path).read_bytes())

def require_text(values:dict[str,object],name:str)->str:
    v=values.get(name)
    if not isinstance(v,str): raise ValueError(f"{name} is not text")
    return v.strip()

def require_decimal(values:dict[str,object],name:str)->Decimal:
    v=values.get(name)
    if not isinstance(v,Decimal): raise ValueError(f"{name} is not decimal")
    return v
