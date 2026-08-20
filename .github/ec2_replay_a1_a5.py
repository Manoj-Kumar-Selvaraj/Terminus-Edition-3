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
OLD_CONTROL = os.environ['OLD_CONTROL']
TASK_HASH = os.environ['TASK_HASH']
CONTROL_HASH = os.environ['CONTROL_HASH']
BASE_DIR = ROOT / '.terminus' / 'executions' / TASK
TEMPLATES = [
    ('WORK_PACKAGE_RESEARCH', 'inv_fa8971c77c11e5b7dd791988950fb9a96d408a1463a33bb41f07d0dc78c2076a'),
    ('SYSTEM_ARCHITECTURE', 'inv_91adb8fc0f80936e03855598353995aabfcff8a1b471d1c5989846a9fca15c3a'),
    ('DEFECT_TOPOLOGY', 'inv_9b138c42e0dc15600dbe2d318198b7b4dcd640a6664acf8414f8344eab6682ad'),
    ('ENVIRONMENT_BUILD', 'inv_75ab63d397a83c46f7a18ff9521c6b8ed5bce8b91492e971c7ec72b8561eda3d'),
    ('REFERENCE_SOLUTION', 'inv_0e29ef2e3264bdf7a9eabbec04670b82a412b8507270d4f1e7c12e71ba07be22'),
    ('VERIFIER_BUILD', 'inv_0eeee2de6e34ef805db0061533bba9518f6c79becc8975efba9425828e4c063c'),
]


def replace(value):
    if isinstance(value, str):
        return value.replace(OLD_CONTROL, CONTROL)
    if isinstance(value, list):
        return [replace(v) for v in value]
    if isinstance(value, dict):
        return {k: replace(v) for k, v in value.items()}
    return value


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def flat_inputs(template: dict) -> dict:
    envelope = replace(template['invocation_snapshot']['inputs'])
    if not isinstance(envelope, dict):
        raise SystemExit('invalid historical input envelope')
    required = envelope.get('required', {})
    optional = envelope.get('optional', {})
    if not isinstance(required, dict) or not isinstance(optional, dict):
        raise SystemExit('historical required/optional inputs are invalid')
    overlap = set(required) & set(optional)
    if overlap:
        raise SystemExit(f'input overlap: {sorted(overlap)}')
    return {**required, **optional}


WORK.mkdir(parents=True, exist_ok=True)
for ordinal, (stage, template_id) in enumerate(TEMPLATES, 1):
    template = json.loads((BASE_DIR / f'{template_id}.result.json').read_text())
    inputs = flat_inputs(template)
    outputs = replace(template['outputs'])
    prefix = WORK / f'{ordinal:02d}-{stage}'
    inp = Path(str(prefix) + '-inputs.json')
    cont = Path(str(prefix) + '-continue.json')
    invp = Path(str(prefix) + '-invocation.json')
    resp = Path(str(prefix) + '-result.json')
    recp = Path(str(prefix) + '-record.json')
    inp.write_text(json.dumps(inputs, indent=2, sort_keys=True) + '\n')

    run('python3', '.terminus/execution/controller_cli.py', 'continue',
        '--task-id', TASK, '--task-commit', TASK_COMMIT,
        '--control-plane-commit', CONTROL,
        '--inputs-json', str(inp), '--output', str(cont))
    payload = json.loads(cont.read_text())
    nxt = payload.get('next', {})
    inv = payload.get('invocation')
    if nxt.get('stage_id') != stage:
        raise SystemExit(f'{stage}: machine route changed: {nxt}')
    if payload.get('execution_mode') != 'INLINE_SPECIALIST':
        raise SystemExit(f'{stage}: mode={payload.get("execution_mode")}')
    if not isinstance(inv, dict) or inv.get('readiness') != 'READY':
        raise SystemExit(f'{stage}: invocation not READY')
    invp.write_text(json.dumps(inv, indent=2, sort_keys=True) + '\n')

    result = {
        'schema_version': '1.0',
        'invocation_id': inv['invocation_id'],
        'output_task_commit': TASK_COMMIT,
        'status': template['status'],
        'outputs': outputs,
        'evidence_refs': [
            {'kind': 'COMMIT', 'ref': f'commit:{TASK_COMMIT}', 'content_hash': TASK_HASH},
            {'kind': 'COMMIT', 'ref': f'commit:{CONTROL}', 'content_hash': CONTROL_HASH},
        ],
    }
    resp.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')

    if stage == 'DEFECT_TOPOLOGY':
        run('python3', '.terminus/validate_defect_topology.py', TASK)
    elif stage == 'ENVIRONMENT_BUILD':
        run('python3', '.terminus/validate_environment_complexity.py', TASK)
        run('python3', '.terminus/validate_runtime_authenticity.py', TASK)
        run('python3', '.terminus/validate_business_module_diversity.py', TASK)
    elif stage == 'VERIFIER_BUILD':
        run('python3', '.terminus/validate_task_complexity.py', TASK)

    run('python3', '.terminus/execution/controller_cli.py', 'record',
        '--invocation', str(invp), '--result', str(resp), '--output', str(recp))
    record = json.loads(recp.read_text())['record']
    if record['stage_id'] != stage or record['status'] != template['status']:
        raise SystemExit(f'{stage}: record mismatch')
    print(f'REPLAYED {stage} invocation={inv["invocation_id"]} record={record["record_id"]}')
