from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from .database import apply_sql,connect,seed_inventory
from .framing import decode_record
from .generation import build_identity,input_manifest
from .layout import load_layout
from .pipeline import PipelineConfig,process

def parser()->argparse.ArgumentParser:
    p=argparse.ArgumentParser(prog="equiv-eval"); sub=p.add_subparsers(dest="command",required=True)
    run=sub.add_parser("run"); run.add_argument("--db",required=True); run.add_argument("--source",required=True); run.add_argument("--layout",required=True); run.add_argument("--business-date",required=True); run.add_argument("--legacy-controls",required=True); run.add_argument("--report-dir",required=True); run.add_argument("--publish-dir",required=True); run.add_argument("--stop-after",type=int)
    init=sub.add_parser("init-db"); init.add_argument("--db",required=True); init.add_argument("--schema",required=True); init.add_argument("--seed",required=True)
    desc=sub.add_parser("describe-layout"); desc.add_argument("--layout",required=True)
    ident=sub.add_parser("identity"); ident.add_argument("--source",required=True); ident.add_argument("--layout",required=True); ident.add_argument("--business-date",required=True)
    return p

def main(argv:list[str]|None=None)->int:
    args=parser().parse_args(argv)
    if args.command=="init-db":
        db=connect(args.db); apply_sql(db,args.schema); apply_sql(db,args.seed); return 0
    if args.command=="describe-layout":
        layout=load_layout(args.layout); print(json.dumps({"layout_id":layout.layout_id,"version":layout.version,"minimum_length":layout.static_min_length(),"fingerprint":layout.fingerprint()})); return 0
    if args.command=="identity":
        print(json.dumps(input_manifest(build_identity(args.source,args.layout,args.business_date)),sort_keys=True)); return 0
    if args.command=="run":
        db=connect(args.db); summary=process(db,PipelineConfig(Path(args.source),Path(args.layout),args.business_date,Path(args.legacy_controls),Path(args.report_dir),Path(args.publish_dir),args.stop_after)); print(json.dumps(summary.as_dict(),sort_keys=True)); return 0 if summary.state.value in {"READY","PUBLISHED"} else 2
    return 2

if __name__=="__main__": raise SystemExit(main())
