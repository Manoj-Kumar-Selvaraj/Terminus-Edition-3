from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json,os,shutil,tempfile

@dataclass(frozen=True)
class ArchiveEntry:
    logical_name:str
    filename:str
    size:int
    sha256:str
def file_hash(path:Path)->str:
    h=sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()
def build_entries(files:dict[str,Path])->tuple[ArchiveEntry,...]:return tuple(ArchiveEntry(name,p.name,p.stat().st_size,file_hash(p)) for name,p in sorted(files.items()))
def archive_generation(generation_id:str,files:dict[str,Path],root:str|Path)->Path:
    root=Path(root);root.mkdir(parents=True,exist_ok=True);target=root/generation_id
    if target.exists():return target
    stage=Path(tempfile.mkdtemp(prefix=f'.archive-{generation_id}-',dir=root))
    try:
        entries=build_entries(files)
        for e in entries:shutil.copy2(files[e.logical_name],stage/e.filename)
        manifest={'generation_id':generation_id,'entries':[e.__dict__ for e in entries]};(stage/'archive.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8');os.replace(stage,target);return target
    except Exception:shutil.rmtree(stage,ignore_errors=True);raise
def verify(path:str|Path)->bool:
    path=Path(path);meta=json.loads((path/'archive.json').read_text(encoding='utf-8'))
    for e in meta['entries']:
        f=path/e['filename']
        if not f.exists() or f.stat().st_size!=e['size'] or file_hash(f)!=e['sha256']:return False
    return True
def archive_files(path:str|Path)->dict[str,Path]:
    path=Path(path);meta=json.loads((path/'archive.json').read_text(encoding='utf-8'));return {e['logical_name']:path/e['filename'] for e in meta['entries']}
