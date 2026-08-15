from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

@dataclass(frozen=True)
class IntegrityEntry:
    logical_name:str
    path:str
    sha256:str
    size:int
@dataclass(frozen=True)
class IntegrityManifest:
    generation_id:str
    entries:tuple[IntegrityEntry,...]
    def by_name(self)->dict[str,IntegrityEntry]:return {e.logical_name:e for e in self.entries}
def hash_file(path:Path)->str:
    h=sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def create(generation_id:str,files:dict[str,Path])->IntegrityManifest:
    return IntegrityManifest(generation_id,tuple(IntegrityEntry(k,str(v),hash_file(v),v.stat().st_size) for k,v in sorted(files.items())))
def validate(manifest:IntegrityManifest)->list[str]:
    issues=[]
    if len(manifest.by_name())!=len(manifest.entries):issues.append('duplicate logical names')
    for e in manifest.entries:
        p=Path(e.path)
        if not p.exists():issues.append(f'missing {e.logical_name}');continue
        if p.stat().st_size!=e.size:issues.append(f'size changed {e.logical_name}')
        elif hash_file(p)!=e.sha256:issues.append(f'hash changed {e.logical_name}')
    return issues
def require_valid(manifest:IntegrityManifest)->None:
    issues=validate(manifest)
    if issues:raise ValueError('; '.join(issues))
def write(manifest:IntegrityManifest,path:str|Path)->None:
    Path(path).write_text(json.dumps({'generation_id':manifest.generation_id,'entries':[e.__dict__ for e in manifest.entries]},indent=2,sort_keys=True)+'\n',encoding='utf-8')
def read(path:str|Path)->IntegrityManifest:
    data=json.loads(Path(path).read_text(encoding='utf-8'));return IntegrityManifest(data['generation_id'],tuple(IntegrityEntry(**e) for e in data['entries']))
