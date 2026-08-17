from __future__ import annotations
import csv, json
from dataclasses import asdict
from pathlib import Path
from .models import ReconciliationResult, RunSummary

def ensure_dir(path:str|Path)->Path:
    p=Path(path); p.mkdir(parents=True,exist_ok=True); return p

def write_summary(summary:RunSummary,path:str|Path)->None:
    Path(path).write_text(json.dumps(summary.as_dict(),indent=2,sort_keys=True)+"\n",encoding="utf-8")

def write_reconciliation(result:ReconciliationResult,path:str|Path)->None:
    Path(path).write_text(json.dumps(result.as_dict(),indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")

def write_rejects(rows,path:str|Path)->None:
    fields=["generation_id","sequence","movement_id","code","message","byte_offset","byte_length"]
    with Path(path).open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=fields); wr.writeheader()
        for r in rows: wr.writerow({k:r[k] for k in fields})

def write_effects(rows,path:str|Path)->None:
    fields=["generation_id","movement_id","sequence","warehouse_id","item_id","quantity_delta","value_delta","effect_kind"]
    with Path(path).open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=fields); wr.writeheader()
        for r in rows: wr.writerow({k:r[k] for k in fields})

def report_paths(root:str|Path)->dict[str,Path]:
    root=ensure_dir(root)
    return {"summary":root/"summary.json","reconciliation":root/"reconciliation.json","rejects":root/"rejects.csv","effects":root/"effects.csv"}
