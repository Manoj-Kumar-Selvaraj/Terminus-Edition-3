#!/usr/bin/env python3
from __future__ import annotations
import os, subprocess
from pathlib import Path

ROOT = Path.cwd()
TARGET = 'task/ec2-artifact-policy-enforcement-lint-fix-20260822'
subprocess.run(['git','fetch','origin',TARGET],check=True)
subprocess.run(['git','checkout','-B','task-fix',f'origin/{TARGET}'],check=True)

p = ROOT/'ec2-artifact-policy-enforcement/tests/test_outputs.py'
text = p.read_text(encoding='utf-8')
needle = '    empty_exceptions,\n'
if text.count(needle) != 1:
    raise SystemExit(f'unexpected empty_exceptions import count={text.count(needle)}')
p.write_text(text.replace(needle,'',1),encoding='utf-8')

p = ROOT/'ec2-artifact-policy-enforcement/tests/verifier_lib.py'
text = p.read_text(encoding='utf-8')
needle = '    if vulnerable is not None:\n        policy = base_policy()\n        if vulnerable:\n'
replacement = '    if vulnerable is not None:\n        if vulnerable:\n'
if text.count(needle) != 1:
    raise SystemExit(f'unexpected changed_scan dead assignment count={text.count(needle)}')
p.write_text(text.replace(needle,replacement,1),encoding='utf-8')

subprocess.run(['python3','-m','pip','install','--quiet','ruff==0.12.8'],check=True)
subprocess.run(['ruff','check','ec2-artifact-policy-enforcement/tests'],check=True)
subprocess.run(['git','diff','--check'],check=True)
subprocess.run(['git','config','user.name','terminus-chat-adapter[bot]'],check=True)
subprocess.run(['git','config','user.email','terminus-chat-adapter[bot]@users.noreply.github.com'],check=True)
subprocess.run(['git','add','--','ec2-artifact-policy-enforcement/tests/test_outputs.py','ec2-artifact-policy-enforcement/tests/verifier_lib.py'],check=True)
subprocess.run(['git','commit','-m','Fix EC2 verifier deterministic preflight lint'],check=True)
subprocess.run(['git','push','origin','HEAD:'+TARGET],check=True)
print('TASK_SNAPSHOT='+subprocess.run(['git','rev-parse','HEAD'],check=True,text=True,capture_output=True).stdout.strip())
