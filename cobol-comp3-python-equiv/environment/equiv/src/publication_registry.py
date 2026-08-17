from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
import json
from .publication import verify_publication

@dataclass(frozen=True)
class PublicationEntry:
    generation_id:str
    path:str
    published_at:str
    manifest_sha256:str
class PublicationRegistry:
    def __init__(self,path:str|Path):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
    def entries(self)->list[PublicationEntry]:
        if not self.path.exists():return []
        return [PublicationEntry(**json.loads(line)) for line in self.path.read_text(encoding='utf-8').splitlines() if line.strip()]
    def get(self,generation_id:str)->PublicationEntry|None:
        rows=[e for e in self.entries() if e.generation_id==generation_id];return rows[-1] if rows else None
    def register(self,generation_id:str,published_path:str|Path)->PublicationEntry:
        path=Path(published_path)
        if not verify_publication(path):raise ValueError('publication integrity check failed')
        existing=self.get(generation_id)
        if existing:
            if Path(existing.path).resolve()!=path.resolve():raise ValueError('generation already registered at different path')
            return existing
        from hashlib import sha256
        manifest=path/'manifest.json';digest=sha256(manifest.read_bytes()).hexdigest();entry=PublicationEntry(generation_id,str(path.resolve()),datetime.now(timezone.utc).isoformat(),digest)
        with self.path.open('a',encoding='utf-8') as f:f.write(json.dumps(entry.__dict__,sort_keys=True)+"\n")
        return entry
    def validate(self)->bool:
        seen=set()
        for e in self.entries():
            if e.generation_id in seen:return False
            seen.add(e.generation_id)
            path=Path(e.path)
            if not path.exists() or not verify_publication(path):return False
            from hashlib import sha256
            if sha256((path/'manifest.json').read_bytes()).hexdigest()!=e.manifest_sha256:return False
        return True
    def generations(self)->tuple[str,...]:return tuple(e.generation_id for e in self.entries())
