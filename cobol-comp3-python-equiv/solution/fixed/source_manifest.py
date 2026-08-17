from __future__ import annotations
from dataclasses import dataclass,asdict
from hashlib import sha256
import json
from pathlib import Path
from .generation import GenerationIdentity

@dataclass(frozen=True)
class SourceManifest:
    generation_id:str
    business_date:str
    source_name:str
    source_size:int
    source_sha256:str
    layout_sha256:str
    record_count:int
    producer:str
    batch_id:str
    def fingerprint(self)->str:
        payload=json.dumps(asdict(self),sort_keys=True,separators=(',',':'))
        return sha256(payload.encode()).hexdigest()
def from_identity(identity:GenerationIdentity,record_count:int,producer:str,batch_id:str)->SourceManifest:
    if record_count<0:raise ValueError('record_count must be non-negative')
    if not producer.strip():raise ValueError('producer required')
    if not batch_id.strip():raise ValueError('batch_id required')
    return SourceManifest(identity.generation_id,identity.business_date,identity.source_name,identity.source_size,identity.source_sha256,identity.layout_sha256,record_count,producer.strip(),batch_id.strip())
def write(manifest:SourceManifest,path:str|Path)->None:
    Path(path).write_text(json.dumps(asdict(manifest)|{'fingerprint':manifest.fingerprint()},indent=2,sort_keys=True)+'\n',encoding='utf-8')
def read(path:str|Path)->SourceManifest:
    data=json.loads(Path(path).read_text(encoding='utf-8'));fingerprint=data.pop('fingerprint',None);manifest=SourceManifest(**data)
    if fingerprint is not None and fingerprint!=manifest.fingerprint():raise ValueError('source manifest fingerprint mismatch')
    return manifest
def validate_against_identity(manifest:SourceManifest,identity:GenerationIdentity)->list[str]:
    problems=[]
    if manifest.generation_id!=identity.generation_id:problems.append('generation_id')
    if manifest.business_date!=identity.business_date:problems.append('business_date')
    if manifest.source_name!=identity.source_name:problems.append('source_name')
    if manifest.source_size!=identity.source_size:problems.append('source_size')
    if manifest.source_sha256!=identity.source_sha256:problems.append('source_sha256')
    if manifest.layout_sha256!=identity.layout_sha256:problems.append('layout_sha256')
    return problems
def require_identity(manifest:SourceManifest,identity:GenerationIdentity)->None:
    problems=validate_against_identity(manifest,identity)
    if problems:raise ValueError('source manifest differs from runtime identity: '+', '.join(problems))
