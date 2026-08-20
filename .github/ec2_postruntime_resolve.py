#!/usr/bin/env python3
import json, pathlib, subprocess
TASK='ec2-artifact-policy-enforcement'
COMMITS=['0ad08868799c19ea2e02458bd2fc92ec64eaa288','232a33a0fbf53f31104d7a54ef6dc2f1ed53d9b7']
root=pathlib.Path.cwd()
def run(args, check=True):
    return subprocess.run(args,cwd=root,text=True,capture_output=True,check=check)
head=run(['git','rev-parse','HEAD']).stdout.strip()
subprocess.run(['python3','.terminus/execution/controller_cli.py','control-plane','--head',head,'--output','/tmp/ec2-control.json'],cwd=root,check=True)
control=json.load(open('/tmp/ec2-control.json'))['control_plane_commit']
out={'main_head':head,'effective_control':control,'task_commits':{}}
for commit in COMMITS:
    p=f'/tmp/ec2-continue-{commit[:8]}.json'
    r=run(['python3','.terminus/execution/controller_cli.py','continue','--task-id',TASK,'--task-commit',commit,'--control-plane-commit',control,'--output',p],check=False)
    value=None
    try: value=json.load(open(p))
    except Exception: value={'stdout':r.stdout,'stderr':r.stderr,'returncode':r.returncode}
    out['task_commits'][commit]=value
print('EC2_POST_RUNTIME_RESOLVE='+json.dumps(out,sort_keys=True))
pathlib.Path('/tmp/ec2-post-runtime-resolve.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
