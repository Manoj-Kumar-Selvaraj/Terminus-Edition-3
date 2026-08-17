from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .framing import determine_record_length,decode_record,RecordDecodeError
from .layout import Layout

@dataclass(frozen=True)
class ScanRecord:
    ordinal:int
    offset:int
    length:int
    decodable:bool
    error:str|None
@dataclass(frozen=True)
class SourceScan:
    source_size:int
    records:tuple[ScanRecord,...]
    trailing_bytes:int
    @property
    def complete_records(self)->int:return sum(1 for r in self.records if r.length>0)
    @property
    def decode_errors(self)->int:return sum(1 for r in self.records if not r.decodable)
    @property
    def fully_framed(self)->bool:return self.trailing_bytes==0 and all(r.length>0 for r in self.records)
def scan_bytes(layout:Layout,payload:bytes)->SourceScan:
    rows=[];offset=0;ordinal=1
    while offset<len(payload):
        length=determine_record_length(layout,payload[offset:])
        if length<=0:
            rows.append(ScanRecord(ordinal,offset,0,False,'indeterminate record boundary'));return SourceScan(len(payload),tuple(rows),len(payload)-offset)
        raw=payload[offset:offset+length]
        try:decode_record(layout,raw,offset);rows.append(ScanRecord(ordinal,offset,length,True,None))
        except RecordDecodeError as exc:rows.append(ScanRecord(ordinal,offset,length,False,str(exc)))
        offset+=length;ordinal+=1
    return SourceScan(len(payload),tuple(rows),0)
def scan_file(layout:Layout,path:str|Path)->SourceScan:return scan_bytes(layout,Path(path).read_bytes())
def offsets(scan:SourceScan)->tuple[int,...]:return tuple(r.offset for r in scan.records)
def lengths(scan:SourceScan)->tuple[int,...]:return tuple(r.length for r in scan.records)
def assert_framed(scan:SourceScan)->None:
    if not scan.fully_framed:raise ValueError(f'source is not fully framed; trailing={scan.trailing_bytes}')
def assert_no_decode_errors(scan:SourceScan)->None:
    bad=[r for r in scan.records if not r.decodable]
    if bad:raise ValueError(f'{len(bad)} record(s) fail decode; first={bad[0].ordinal}:{bad[0].error}')
