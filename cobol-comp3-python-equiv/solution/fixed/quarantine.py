from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path

@dataclass(frozen=True)
class QuarantineRecord:
    generation_id:str
    sequence:int
    byte_offset:int
    byte_length:int
    error_code:str
    error_message:str
    raw_sha256:str
    raw_hex:str
    captured_at:str
    def key(self)->str:return f'{self.generation_id}:{self.sequence}:{self.raw_sha256}'
def capture(generation_id:str,sequence:int,offset:int,length:int,code:str,message:str,raw:bytes)->QuarantineRecord:
    return QuarantineRecord(generation_id,sequence,offset,length,code,message,sha256(raw).hexdigest(),raw.hex(),datetime.now(timezone.utc).isoformat())
class QuarantineStore:
    def __init__(self,path:str|Path):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
    def append(self,record:QuarantineRecord)->None:
        existing={r.key() for r in self.records()}
        if record.key() in existing:return
        with self.path.open('a',encoding='utf-8') as f:f.write(json.dumps(asdict(record),sort_keys=True)+"\n")
    def records(self)->list[QuarantineRecord]:
        if not self.path.exists():return []
        return [QuarantineRecord(**json.loads(line)) for line in self.path.read_text(encoding='utf-8').splitlines() if line.strip()]
    def generation(self,generation_id:str)->list[QuarantineRecord]:return [r for r in self.records() if r.generation_id==generation_id]
    def by_code(self,code:str)->list[QuarantineRecord]:return [r for r in self.records() if r.error_code==code]
    def verify_hashes(self)->bool:
        for r in self.records():
            try:raw=bytes.fromhex(r.raw_hex)
            except ValueError:return False
            if sha256(raw).hexdigest()!=r.raw_sha256:return False
        return True
    def summary(self,generation_id:str)->dict[str,object]:
        rows=self.generation(generation_id);codes={}
        for r in rows:codes[r.error_code]=codes.get(r.error_code,0)+1
        return {'generation_id':generation_id,'records':len(rows),'codes':codes,'hashes_valid':self.verify_hashes()}
