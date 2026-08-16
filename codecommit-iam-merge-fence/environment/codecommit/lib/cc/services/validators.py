from __future__ import annotations
import re
from typing import Any
from cc.util import full_ref

REPO_RE = re.compile(r'^[a-z][a-z0-9-]{1,62}$')
PRINCIPAL_RE = re.compile(r'^[a-z][a-z0-9_\-]{1,63}$')

def validate_repo_name(name: str) -> str:
    if not REPO_RE.match(name):
        raise ValueError(f'invalid repo name: {name}')
    return name

def validate_principal(name: str) -> str:
    if not PRINCIPAL_RE.match(name):
        raise ValueError(f'invalid principal: {name}')
    return name

def validate_ref(ref: str) -> str:
    r = full_ref(ref)
    if not r.startswith('refs/heads/'):
        raise ValueError(f'unsupported ref: {ref}')
    return r

def validate_approval_rule(rule: dict[str, Any]) -> dict[str, Any]:
    for key in ('repo','destination','required','pool'):
        if key not in rule:
            raise ValueError(f'missing approval rule field: {key}')
    if int(rule['required']) < 1:
        raise ValueError('required must be >= 1')
    if not isinstance(rule['pool'], list) or not rule['pool']:
        raise ValueError('pool must be non-empty list')
    rule = dict(rule)
    rule['destination'] = full_ref(str(rule['destination']))
    return rule

def validate_pipeline_binding(b: dict[str, Any]) -> dict[str, Any]:
    for key in ('repo','ref','pipeline'):
        if key not in b:
            raise ValueError(f'missing binding field: {key}')
    out=dict(b)
    out['ref']=full_ref(str(b['ref']))
    return out

def validate_webhook(w: dict[str, Any]) -> dict[str, Any]:
    for key in ('id','url'):
        if key not in w:
            raise ValueError(f'missing webhook field: {key}')
    return dict(w)
