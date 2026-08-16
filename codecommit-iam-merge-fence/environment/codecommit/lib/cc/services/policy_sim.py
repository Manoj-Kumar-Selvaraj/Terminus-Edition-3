from __future__ import annotations
from typing import Any
from cc.iam import actions, conditions, policy
from cc.iam.context import build_context

def simulate(principal: str, action: str, repo: str, reference: str, *, mfa: bool=False, source_ip: str='127.0.0.1', fixed: bool=False) -> dict[str, Any]:
    ctx = build_context(principal, action, repo, reference, mfa=mfa, source_ip=source_ip)
    statements = policy.statements_for_principal(principal)
    matched=[]
    for stmt in statements:
        sa=stmt.get('Action','')
        ok_action = actions.action_matches_fixed(sa, action) if fixed else actions.action_matches(sa, action)
        if not ok_action:
            continue
        resource=str(stmt.get('Resource',''))
        star = sa in ('*','codecommit:*')
        if fixed:
            ok_res = policy.resource_matches_fixed(resource, ctx.resource_arn)
        else:
            ok_res = policy.resource_matches(resource, ctx.resource_arn, star_waives=star)
        if not ok_res:
            matched.append({'policy': stmt.get('_policy_id'), 'stage':'resource', 'ok':False})
            continue
        ok_cond = conditions.conditions_match(stmt.get('Condition'), ctx.as_eval_map(), fixed=fixed)
        matched.append({'policy': stmt.get('_policy_id'), 'effect': stmt.get('Effect'), 'action': sa, 'resource': resource, 'conditions_ok': ok_cond})
    return {'principal': principal, 'action': action, 'resource': ctx.resource_arn, 'reference': ctx.reference, 'matches': matched}
