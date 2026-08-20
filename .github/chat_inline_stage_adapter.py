#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path.cwd()
WORK = Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'chat-inline'
WORK.mkdir(parents=True, exist_ok=True)


def run(*args: str, capture: bool = False) -> str:
    cp = subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=capture)
    return cp.stdout.strip() if capture else ''


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')


def remote_main() -> str:
    return run('git','ls-remote','origin','refs/heads/main', capture=True).split()[0]

sha = os.environ['GITHUB_SHA']
branch = os.environ['GITHUB_REF_NAME']
changed = run('git','diff-tree','--no-commit-id','--name-only','-r',sha,'--','.terminus/chat-exec/*.json', capture=True).splitlines()
if len(changed) != 1:
    raise SystemExit(f'expected exactly one chat-exec request, found {changed}')
req = load(ROOT / changed[0])
required = {'schema_version','mode','task_id','task_commit','control_plane_commit','expected_repository_head','stage_id','inputs','result'}
if set(req) != required or req['schema_version'] != '1.0':
    raise SystemExit('invalid adapter request')

task=req['task_id']; task_commit=req['task_commit']; control=req['control_plane_commit']; stage=req['stage_id']; mode=req['mode']; expected=req['expected_repository_head']
if remote_main() != expected:
    raise SystemExit(f'main moved before adapter execution expected={expected} current={remote_main()}')

dump(WORK/'request.json', req)
dump(WORK/'inputs.json', req['inputs'])
dump(WORK/'result-template.json', req['result'])
run('git','checkout','--detach',expected)
run('python3','.terminus/execution/controller_cli.py','control-plane','--head',expected,'--output',str(WORK/'control-plane.json'))
resolved = load(WORK/'control-plane.json')['control_plane_commit']
if resolved != control:
    raise SystemExit(f'control-plane mismatch {resolved} != {control}')
run('python3','.terminus/execution/controller_cli.py','continue','--task-id',task,'--task-commit',task_commit,'--control-plane-commit',control,'--inputs-json',str(WORK/'inputs.json'),'--output',str(WORK/'continue.json'))
cont=load(WORK/'continue.json')
if cont.get('next',{}).get('stage_id') != stage:
    raise SystemExit(f'machine stage changed: {cont.get("next")}')
inv=cont.get('invocation')
if not isinstance(inv,dict) or inv.get('readiness') != 'READY' or inv.get('stage',{}).get('stage_id') != stage:
    raise SystemExit('invocation not READY for expected stage')
if cont.get('execution_mode') not in {'INLINE_SPECIALIST','INLINE_SPECIALIST_SEQUENCE','ORCHESTRATOR_DIRECT'}:
    raise SystemExit(f'unsupported execution mode {cont.get("execution_mode")}')
dump(WORK/'invocation.json',inv)

if stage == 'HUMAN_WRITING_RESEARCH':
    run('python3','.terminus/human_writing/calibration_cli.py','--root','.','plan','--task-id',task,'--domain','terraform ansible provider platform cloud infrastructure linux managed resources lifecycle','--output',str(WORK/'calibration-pair.json'))

if mode == 'RECORD':
    result=req['result']
    result['schema_version']='1.0'; result['invocation_id']=inv['invocation_id']; result.setdefault('output_task_commit',task_commit)
    if stage == 'HUMAN_WRITING_RESEARCH':
        pair=load(WORK/'calibration-pair.json'); writer=pair['writer']; reviewer=pair['reviewer']
        approval={'approved':True,'approved_by':'CI_ORCHESTRATOR','reason':'No approved external human-writing cache was supplied; repository policy permits deterministic local calibration with explicit DEGRADED coverage and no claim of FULL external coverage.'}
        task_profile={'voice':'direct platform engineering change request','structure':['state the inherited provider objective first','preserve exact public contracts and hard safety/state constraints','reference solver-visible technical contracts instead of reproducing hidden verifier rows','keep implementation-neutral observable outcomes'],'must_preserve':['ten documented resource interfaces','stable external-object identity','Ansible mutation versus native observation boundary','transactional state publication and retry semantics','scoped ownership/deletion','runner process safety','normalization/idempotency','Terraform Core sole durable state authority'],'avoid':['invented incidents or personal claims','rubric-like hidden-test enumeration','style-driven omission of lifecycle constraints','copied distinctive source wording']}
        profile={'DATASET_POLICY_VERSION':'1.2','DATASET_REGISTRY_SHA256':pair['registry_sha256'],'SEED_CATALOG_SHA256':pair['catalog_sha256'],'DOMAIN_PROFILES_SHA256':pair['domain_profiles_sha256'],'DOMAIN_PROFILE':pair['domain_profile'],'CALIBRATION_PAIR_ID':pair['pair_id'],'WRITER_CALIBRATION_ID':writer['calibration_id'],'REVIEWER_CALIBRATION_ID':reviewer['calibration_id'],'WRITER_SAMPLE_IDS':writer['local_seed_sample_ids'],'REVIEWER_SAMPLE_IDS':reviewer['local_seed_sample_ids'],'WRITER_REVIEWER_SAMPLE_OVERLAP':[],'EXTERNAL_DATASET_COVERAGE':'DEGRADED','TASK_WRITING_PROFILE':task_profile,'CACHE_SOURCE_KEYS_USED':[],'RAW_SOURCE_KEYS_USED_FOR_CONTAMINATION':[],'DEGRADED_COVERAGE_APPROVAL':approval,'CURRENT_STATE_EVIDENCE_NOTES':['Current deterministic repository planner generated the pair for this task/domain.','No Oracle, verifier-private, prior-review, model-trial, or private defect evidence was consumed by A6.']}
        research=ROOT/'.terminus'/'research'; research.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(WORK/'calibration-pair.json', research/f'{task}-dataset-calibration.json')
        dump(research/f'{task}-task-writing-profile.json', profile)
        result['outputs']=profile
    dump(WORK/'result.json',result)

    if stage == 'DEFECT_TOPOLOGY': run('python3','.terminus/validate_defect_topology.py',task)
    elif stage == 'ENVIRONMENT_BUILD':
        run('python3','.terminus/validate_environment_complexity.py',task); run('python3','.terminus/validate_runtime_authenticity.py',task); run('python3','.terminus/validate_business_module_diversity.py',task)
    elif stage in {'VERIFIER_BUILD','COMPLEXITY_GATE'}: run('python3','.terminus/validate_task_complexity.py',task)
    elif stage == 'RUNTIME_AUTHENTICITY':
        run('python3','.terminus/validate_runtime_authenticity.py',task); run('python3','.terminus/validate_business_module_diversity.py',task)
    elif stage in {'HUMAN_WRITING_RESEARCH','INSTRUCTION_DRAFT'}:
        run('python3','.terminus/human_writing/validate_calibration.py','--root','.','--pair',f'.terminus/research/{task}-dataset-calibration.json','--profile',f'.terminus/research/{task}-task-writing-profile.json')

    run('python3','.terminus/execution/controller_cli.py','record','--invocation',str(WORK/'invocation.json'),'--result',str(WORK/'result.json'),'--output',str(WORK/'record.json'))
    porcelain=run('git','status','--porcelain',capture=True).splitlines()
    allowed=(f'.terminus/executions/{task}',f'.terminus/workflows/{task}',f'.terminus/research/{task}-dataset-calibration.json',f'.terminus/research/{task}-task-writing-profile.json')
    unexpected=[line[3:] for line in porcelain if not line[3:].startswith(allowed)]
    if unexpected: raise SystemExit(f'unexpected mutations: {unexpected}')
    run('git','config','user.name','terminus-chat-adapter[bot]'); run('git','config','user.email','terminus-chat-adapter[bot]@users.noreply.github.com')
    run('git','add','--',f'.terminus/executions/{task}')
    if stage == 'HUMAN_WRITING_RESEARCH': run('git','add','--',f'.terminus/research/{task}-dataset-calibration.json',f'.terminus/research/{task}-task-writing-profile.json')
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode == 0: raise SystemExit('no canonical record mutation')
    run('git','commit','-m',f'Record {task} {stage} inline result')
    if remote_main() != expected: raise SystemExit(f'main moved during record expected={expected} current={remote_main()}')
    run('git','push','origin','HEAD:main')

run('git','fetch','origin',branch)
run('git','checkout','-B','chat-diagnostics',f'origin/{branch}')
diag=ROOT/'.terminus'/'chat-results'/task/stage; diag.mkdir(parents=True,exist_ok=True)
for name in ('continue.json','invocation.json','calibration-pair.json','result.json','record.json'):
    src=WORK/name
    if src.exists(): shutil.copyfile(src,diag/name)
run('git','config','user.name','terminus-chat-adapter[bot]'); run('git','config','user.email','terminus-chat-adapter[bot]@users.noreply.github.com')
run('git','add','--',str(diag.relative_to(ROOT)))
if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode != 0:
    run('git','commit','-m',f'Persist chat diagnostics for {task} {stage}')
    run('git','push','origin','HEAD:'+branch)
