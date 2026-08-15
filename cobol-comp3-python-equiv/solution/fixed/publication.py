from __future__ import annotations
from hashlib import sha256
import json, os, shutil, tempfile
from pathlib import Path
from .models import ReconciliationResult

def hash_file(path:Path)->str:
    h=sha256();
    with path.open("rb") as f:
        for b in iter(lambda:f.read(65536),b""): h.update(b)
    return h.hexdigest()

def build_manifest(generation_id:str,files:dict[str,Path])->dict:
    return {"generation_id":generation_id,"files":{name:{"name":path.name,"size":path.stat().st_size,"sha256":hash_file(path)} for name,path in sorted(files.items())}}

def atomic_publish(generation_id:str,files:dict[str,Path],reconciliation:ReconciliationResult,destination:str|Path)->Path:
    if not reconciliation.passed: raise ValueError("cannot publish failed reconciliation")
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    target=destination/generation_id
    if target.exists():
        existing=target/"manifest.json"
        if not existing.exists(): raise ValueError("existing publication missing manifest")
        manifest=json.loads(existing.read_text(encoding="utf-8"))
        if manifest["generation_id"]!=generation_id: raise ValueError("publication generation mismatch")
        return target
    staging=Path(tempfile.mkdtemp(prefix=f".{generation_id}.",dir=destination))
    try:
        copied={}
        for name,src in files.items():
            dst=staging/src.name; shutil.copy2(src,dst); copied[name]=dst
        manifest=build_manifest(generation_id,copied); (staging/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        os.replace(staging,target); return target
    except Exception:
        shutil.rmtree(staging,ignore_errors=True); raise

def verify_publication(path:str|Path)->bool:
    path=Path(path); manifest=json.loads((path/"manifest.json").read_text(encoding="utf-8"))
    for meta in manifest["files"].values():
        f=path/meta["name"]
        if not f.exists() or f.stat().st_size!=meta["size"] or hash_file(f)!=meta["sha256"]: return False
    return True
