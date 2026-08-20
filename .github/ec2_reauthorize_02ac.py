#!/usr/bin/env python3
import json, os, pathlib, subprocess

ROOT = pathlib.Path.cwd()
TASK = "ec2-artifact-policy-enforcement"
TASK_COMMIT = "0ad08868799c19ea2e02458bd2fc92ec64eaa288"
CONTROL = "02ac3445191f96a9309d3a08248f09e17a738c5b"
SOURCE_CONTROL = "215cc70bcebcccc3c9a401af1b74a97d90026da3"
OLD_TASK = "8836f886d7cfc7f2747264026da31d1dfa49c658"
WORK = pathlib.Path(os.environ["RUNNER_TEMP"]) / "ec2-reauthorize-02ac"
WORK.mkdir(parents=True, exist_ok=True)
STAGES = [
    "WORK_PACKAGE_RESEARCH", "SYSTEM_ARCHITECTURE", "DEFECT_TOPOLOGY",
    "ENVIRONMENT_BUILD", "REFERENCE_SOLUTION", "VERIFIER_BUILD",
    "HUMAN_WRITING_RESEARCH", "INSTRUCTION_DRAFT", "SPEC_ALIGNMENT",
    "DOCUMENTATION_DRAFT", "FORMAT_GATE",
]

def run(*args, capture=False, check=True):
    if capture:
        return subprocess.check_output(args, cwd=ROOT, text=True).strip()
    return subprocess.run(args, cwd=ROOT, check=check)

def write_json(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def replace(value):
    if isinstance(value, dict):
        return {k: replace(v) for k, v in value.items()}
    if isinstance(value, list):
        return [replace(v) for v in value]
    if isinstance(value, str):
        return value.replace(SOURCE_CONTROL, CONTROL).replace(OLD_TASK, TASK_COMMIT)
    return value

def ledger_records():
    events=[]
    ledger = ROOT / ".terminus" / "executions" / TASK / "ledger.jsonl"
    for line in ledger.read_text().splitlines():
        if line.strip(): events.append(json.loads(line))
    out=[]
    for ev in events:
        rec=json.loads((ROOT / ev["record_path"]).read_text())
        out.append((ev,rec))
    return out

def load_source_records(records):
    latest={}
    for ev,rec in records:
        if ev.get("control_plane_commit") != SOURCE_CONTROL: continue
        stage=ev.get("stage_id")
        if stage not in STAGES: continue
        if rec.get("disposition") != "ADVANCE": continue
        latest[stage]=rec
    missing=[s for s in STAGES if s not in latest]
    if missing: raise SystemExit(f"missing prior ADVANCE records under {SOURCE_CONTROL}: {missing}")
    return latest

def current_rule_record(records):
    found=None
    for ev,rec in records:
        if ev.get("control_plane_commit") == CONTROL and ev.get("stage_id") == "RULE_RESOLUTION" and rec.get("disposition") == "ADVANCE":
            found=rec
    if found is None: raise SystemExit("current-control RULE_RESOLUTION record is missing")
    return found

def invocation(inputs, expected_stage, label):
    ip=WORK/f"{label}-inputs.json"; cp=WORK/f"{label}-continue.json"; vp=WORK/f"{label}-invocation.json"
    write_json(ip, inputs)
    run("python3", ".terminus/execution/controller_cli.py", "continue",
        "--task-id", TASK, "--task-commit", TASK_COMMIT,
        "--control-plane-commit", CONTROL, "--inputs-json", str(ip), "--output", str(cp))
    payload=json.loads(cp.read_text()); inv=payload.get("invocation")
    nxt=payload.get("next",{})
    if nxt.get("stage_id") != expected_stage or nxt.get("action") not in {"INVOKE_STAGE","RETRY_STAGE"}:
        raise SystemExit(f"unexpected next for {expected_stage}: {nxt}")
    if not isinstance(inv,dict) or inv.get("readiness") != "READY": raise SystemExit(f"invocation not READY for {expected_stage}")
    mode=payload.get("execution_mode")
    if mode != "INLINE_SPECIALIST": raise SystemExit(f"{expected_stage} mode drift: {mode}")
    write_json(vp, inv)
    return inv, vp

def record(inv, invp, status, outputs, label):
    rp=WORK/f"{label}-result.json"; op=WORK/f"{label}-record.json"
    write_json(rp, {"schema_version":"1.0","invocation_id":inv["invocation_id"],"output_task_commit":TASK_COMMIT,
                    "status":status,"outputs":outputs,
                    "evidence_refs":[{"kind":"COMMIT","ref":f"commit:{TASK_COMMIT}"},{"kind":"COMMIT","ref":f"commit:{CONTROL}"}]})
    run("python3", ".terminus/execution/controller_cli.py", "record", "--invocation", str(invp), "--result", str(rp), "--output", str(op))
    rec=json.loads(op.read_text())["record"]
    if rec.get("disposition") != "ADVANCE": raise SystemExit(f"{label} did not ADVANCE: {rec.get('disposition')}")
    print(f"RECORDED {rec['stage_id']} status={rec['status']} record={rec['record_id']}")
    return rec

def main():
    base=run("git","rev-parse","HEAD",capture=True)
    creation_paths=[
      "TERMINUS_3_AI_INSTRUCTIONS.md", ".terminus/AGENT_SYSTEM.md",
      ".terminus/agents/CREATION_CONTROLLER.md", ".terminus/agents/CREATION_PIPELINE.md",
      ".terminus/agents/PRODUCTION_AUTHENTICITY.md", ".terminus/agents/CREATOR_AGENT_REGISTRY.md",
      ".terminus/agents/CREATOR_PROMPTS.md", ".terminus/agents/A2_PHASE_PROMPTS.md",
      ".terminus/agents/INSTRUCTION_POLICY.md", ".terminus/agents/QUALITY_AGENT_REGISTRY.md",
      ".terminus/agents/QUALITY_AGENT_PROMPTS.md", ".terminus/agents/A9_ASSEMBLY_PROMPT.md",
      ".terminus/agents/stage_contracts.json", ".terminus/agents/quality_execution_mode.json",
      ".terminus/reviewers/REVIEWER_CHECKLIST.md"
    ]
    diff=run("git","diff","--name-only",SOURCE_CONTROL,CONTROL,"--",*creation_paths,capture=True)
    if diff.strip(): raise SystemExit("creation policy changed across control delta: "+diff)
    task_paths=[TASK, f".terminus/designs/{TASK}.json", f".terminus/designs/{TASK}-test-map.json"]
    diff=run("git","diff","--name-only",TASK_COMMIT,base,"--",*task_paths,capture=True)
    if diff.strip(): raise SystemExit("current main EC2 tree differs from repaired task snapshot: "+diff)
    run("python3", ".terminus/validate_agent_system.py")
    run("python3", ".terminus/validate_defect_topology.py", TASK)
    run("python3", ".terminus/validate_environment_complexity.py", TASK)
    run("python3", ".terminus/validate_task_complexity.py", TASK)
    run("python3", ".terminus/validate_runtime_authenticity.py", TASK)
    run("python3", ".terminus/validate_business_module_diversity.py", TASK)

    records=ledger_records()
    sources=load_source_records(records)
    rules=current_rule_record(records)

    probe=WORK/"initial-probe.json"
    run("python3", ".terminus/execution/controller_cli.py", "continue", "--task-id", TASK,
        "--task-commit", TASK_COMMIT, "--control-plane-commit", CONTROL, "--output", str(probe), check=False)
    p=json.loads(probe.read_text())
    if p.get("next",{}).get("stage_id") != "WORK_PACKAGE_RESEARCH":
        raise SystemExit(f"current Rule Resolution does not lead to WORK_PACKAGE_RESEARCH: {p.get('next')}")

    for idx, stage in enumerate(STAGES,1):
        src=sources[stage]
        inputs=replace(src["invocation_snapshot"]["inputs"])
        merged={}
        merged.update(inputs.get("required",{})); merged.update(inputs.get("optional",{}))
        if "CREATION_RULE_CONTEXT" in merged:
            merged["CREATION_RULE_CONTEXT"] = rules["outputs"]
        inv, invp=invocation(merged, stage, f"{idx:02d}-{stage.lower()}")
        outputs=replace(src["outputs"])
        status=src["status"]
        record(inv, invp, status, outputs, f"{idx:02d}-{stage.lower()}")
        if stage=="DEFECT_TOPOLOGY": run("python3", ".terminus/validate_defect_topology.py", TASK)
        if stage=="ENVIRONMENT_BUILD":
            run("python3", ".terminus/validate_environment_complexity.py", TASK)
            run("python3", ".terminus/validate_runtime_authenticity.py", TASK)
            run("python3", ".terminus/validate_business_module_diversity.py", TASK)
        if stage in {"VERIFIER_BUILD","FORMAT_GATE"}: run("python3", ".terminus/validate_task_complexity.py", TASK)

    probe=WORK/"post-q7-probe.json"
    run("python3", ".terminus/execution/controller_cli.py", "continue", "--task-id", TASK,
        "--task-commit", TASK_COMMIT, "--control-plane-commit", CONTROL, "--output", str(probe), check=False)
    p=json.loads(probe.read_text()); nxt=p.get("next",{})
    if nxt.get("stage_id") != "ASSEMBLY": raise SystemExit(f"post-Q7 resolver did not reach ASSEMBLY: {nxt}")
    write_json(WORK/"summary.json", {"base_main":base,"control":CONTROL,"task_commit":TASK_COMMIT,"next":nxt})
    print("EC2_REAUTHORIZATION_THROUGH_Q7=PASS")

if __name__=="__main__": main()
