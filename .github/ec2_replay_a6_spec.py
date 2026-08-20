#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('.')
WORK = Path(sys.argv[1])
TASK = os.environ['TASK']
TASK_COMMIT = os.environ['TASK_COMMIT']
CONTROL = os.environ['CONTROL_COMMIT']
TASK_HASH = os.environ['TASK_HASH']
CONTROL_HASH = os.environ['CONTROL_HASH']
BASE = ROOT / '.terminus' / 'executions' / TASK

STAGES = [
    ('HUMAN_WRITING_RESEARCH', 'inv_a49eeb8c6826e35307d241a6ae6292258e2d8d5e020cefac01af865645643ca1', {'4cc1f68cb57b284c4817e3f354ea6eb74c5f717d'}),
    ('INSTRUCTION_DRAFT', 'inv_611aaf0f821f82e0c855cf56fe29f5d655d7d0ae4c620ae5abca667e278bd83a', {'4cc1f68cb57b284c4817e3f354ea6eb74c5f717d'}),
    ('SPEC_ALIGNMENT', 'inv_b0dce300e0742ae84b075476a8db0ef95ff18c4db532ca1a2218d204c58b9892', {'5106b27ae6cc5257854f08c63bac4eca95685f36','4cc1f68cb57b284c4817e3f354ea6eb74c5f717d'}),
]


def replace(value, old_controls):
    if isinstance(value, str):
        for old in old_controls:
            value = value.replace(old, CONTROL)
        return value
    if isinstance(value, list):
        return [replace(v, old_controls) for v in value]
    if isinstance(value, dict):
        return {k: replace(v, old_controls) for k, v in value.items()}
    return value


def flat_inputs(template, old_controls):
    envelope = replace(template['invocation_snapshot']['inputs'], old_controls)
    required = envelope.get('required', {})
    optional = envelope.get('optional', {})
    if not isinstance(required, dict) or not isinstance(optional, dict):
        raise SystemExit('invalid input envelope')
    return {**required, **optional}


def run(*args: str):
    subprocess.run(args, cwd=ROOT, check=True)


WORK.mkdir(parents=True, exist_ok=True)
for ordinal, (stage, template_id, old_controls) in enumerate(STAGES, 1):
    template = json.loads((BASE / f'{template_id}.result.json').read_text())
    inputs = flat_inputs(template, old_controls)
    outputs = replace(template['outputs'], old_controls)
    prefix = WORK / f'{ordinal:02d}-{stage}'
    inp = Path(str(prefix) + '-inputs.json')
    cont = Path(str(prefix) + '-continue.json')
    invp = Path(str(prefix) + '-invocation.json')
    resp = Path(str(prefix) + '-result.json')
    recp = Path(str(prefix) + '-record.json')
    inp.write_text(json.dumps(inputs, indent=2, sort_keys=True) + '\n')
    run('python3','.terminus/execution/controller_cli.py','continue',
        '--task-id',TASK,'--task-commit',TASK_COMMIT,'--control-plane-commit',CONTROL,
        '--inputs-json',str(inp),'--output',str(cont))
    payload = json.loads(cont.read_text())
    inv = payload.get('invocation')
    if payload.get('next',{}).get('stage_id') != stage:
        raise SystemExit(f'{stage}: machine route changed: {payload.get("next")}')
    expected_mode = 'INLINE_SPECIALIST_SEQUENCE' if stage == 'SPEC_ALIGNMENT' else 'INLINE_SPECIALIST'
    if payload.get('execution_mode') != expected_mode:
        raise SystemExit(f'{stage}: mode={payload.get("execution_mode")} expected={expected_mode}')
    if not isinstance(inv,dict) or inv.get('readiness') != 'READY':
        raise SystemExit(f'{stage}: invocation not READY')
    if stage == 'SPEC_ALIGNMENT':
        sequence = payload.get('inline_specialist_sequence',{}).get('steps',[])
        roles = [step.get('role_id') for step in sequence]
        expected_roles = ['Q1_SPEC_GAP_REPAIRER','Q2_VERIFIER_COVERAGE_REPAIRER','Q3_SPEC_AMBIGUITY_REPAIRER']
        if roles != expected_roles:
            raise SystemExit(f'SPEC_ALIGNMENT sequence drift: {roles}')
        if outputs.get('Q1_STATUS') not in {'NO_GAP','PASS'} or outputs.get('Q2_STATUS') not in {'COVERED','PASS'} or outputs.get('Q3_STATUS') not in {'CLEAR','PASS'}:
            raise SystemExit(f'SPEC_ALIGNMENT historical semantic result no longer satisfied: {outputs}')
    invp.write_text(json.dumps(inv,indent=2,sort_keys=True)+'\n')

    if stage in {'HUMAN_WRITING_RESEARCH','INSTRUCTION_DRAFT'}:
        run('python3','.terminus/human_writing/validate_calibration.py','--root','.',
            '--pair',f'.terminus/research/{TASK}-dataset-calibration.json',
            '--profile',f'.terminus/research/{TASK}-task-writing-profile.json')

    result = {
        'schema_version':'1.0',
        'invocation_id':inv['invocation_id'],
        'output_task_commit':TASK_COMMIT,
        'status':template['status'],
        'outputs':outputs,
        'evidence_refs':[
            {'kind':'COMMIT','ref':f'commit:{TASK_COMMIT}','content_hash':TASK_HASH},
            {'kind':'COMMIT','ref':f'commit:{CONTROL}','content_hash':CONTROL_HASH},
        ],
    }
    resp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    run('python3','.terminus/execution/controller_cli.py','record','--invocation',str(invp),'--result',str(resp),'--output',str(recp))
    record = json.loads(recp.read_text())['record']
    if record['stage_id'] != stage or record['status'] != template['status']:
        raise SystemExit(f'{stage}: record mismatch')
    print(f'REPLAYED {stage} invocation={inv["invocation_id"]} record={record["record_id"]}')
