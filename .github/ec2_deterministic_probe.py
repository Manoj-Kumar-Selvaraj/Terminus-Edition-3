#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess
from pathlib import Path

ROOT = Path.cwd()
sha = os.environ['GITHUB_SHA']
changed = subprocess.run(
    ['git','diff-tree','--no-commit-id','--name-only','-r',sha,'--','.terminus/chat-exec/*.json'],
    check=True,text=True,capture_output=True,
).stdout.splitlines()
if len(changed) != 1:
    raise SystemExit(f'expected one chat-exec request, got {changed}')
req = json.loads((ROOT / changed[0]).read_text(encoding='utf-8'))
task=req['task_id']; task_commit=req['task_commit']; control=req['control_plane_commit']
subprocess.run(['git','fetch','origin','main'],check=True)
head=subprocess.run(['git','rev-parse','origin/main'],check=True,text=True,capture_output=True).stdout.strip()
# Ensure current main still contains the exact logical task tree.
requested_tree=subprocess.run(['git','rev-parse',f'{task_commit}:{task}'],check=True,text=True,capture_output=True).stdout.strip()
current_tree=subprocess.run(['git','rev-parse',f'{head}:{task}'],check=True,text=True,capture_output=True).stdout.strip()
if requested_tree != current_tree:
    raise SystemExit(f'task tree drift requested={task_commit} head={head}')
work=Path(os.environ.get('RUNNER_TEMP','/tmp'))/'ec2-det-probe'; work.mkdir(parents=True,exist_ok=True)
subprocess.run(['python3','.terminus/execution/controller_cli.py','control-plane','--head',head,'--output',str(work/'control.json')],check=True)
resolved=json.loads((work/'control.json').read_text())['control_plane_commit']
if resolved != control:
    raise SystemExit(f'control drift requested={control} resolved={resolved}')
(work/'inputs.json').write_text(json.dumps(req['inputs'],indent=2,sort_keys=True)+'\n',encoding='utf-8')
subprocess.run([
    'python3','.terminus/execution/controller_cli.py','continue',
    '--task-id',task,'--task-commit',task_commit,
    '--control-plane-commit',control,'--inputs-json',str(work/'inputs.json'),
    '--output',str(work/'continue.json')
],check=True)
cont=json.loads((work/'continue.json').read_text())
print('CURRENT_HEAD='+head)
print('RESOLVED_CONTROL='+resolved)
print('NEXT='+json.dumps(cont.get('next'),sort_keys=True,separators=(',',':')))
print('EXECUTION_MODE='+str(cont.get('execution_mode')))
print('INVOCATION='+json.dumps(cont.get('invocation'),sort_keys=True,separators=(',',':')))
print('DISPATCH='+json.dumps(cont.get('dispatch'),sort_keys=True,separators=(',',':')))
