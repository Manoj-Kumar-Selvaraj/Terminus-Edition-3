from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .models import RunState

class Role(str,Enum):PLATFORM='PLATFORM';WAREHOUSE='WAREHOUSE';FINANCE='FINANCE';OPERATIONS='OPERATIONS';AUDITOR='AUDITOR'
@dataclass(frozen=True)
class Principal:
    name:str
    roles:frozenset[Role]
@dataclass(frozen=True)
class AuthorizationDecision:
    allowed:bool
    action:str
    required:frozenset[Role]
    present:frozenset[Role]
    reason:str
ACTION_ROLES={'RUN':frozenset({Role.PLATFORM,Role.WAREHOUSE}),'RECONCILE':frozenset({Role.FINANCE,Role.PLATFORM}),'PUBLISH':frozenset({Role.OPERATIONS,Role.FINANCE}),'RESTART':frozenset({Role.PLATFORM,Role.OPERATIONS}),'OVERRIDE_HOLD':frozenset({Role.FINANCE,Role.OPERATIONS}),'VIEW_AUDIT':frozenset({Role.AUDITOR,Role.OPERATIONS})}
def decide(principal:Principal,action:str,state:RunState|None=None)->AuthorizationDecision:
    required=ACTION_ROLES.get(action)
    if required is None:return AuthorizationDecision(False,action,frozenset(),principal.roles,'unknown action')
    present=principal.roles & required
    allowed=bool(present)
    if action=='PUBLISH' and state!=RunState.READY:allowed=False;reason='publication requires READY state'
    elif action=='OVERRIDE_HOLD' and state!=RunState.HELD:allowed=False;reason='hold override requires HELD state'
    elif not present:reason=f'action requires one of {sorted(r.value for r in required)}'
    else:reason='authorized'
    return AuthorizationDecision(allowed,action,required,present,reason)
def require(principal:Principal,action:str,state:RunState|None=None)->None:
    decision=decide(principal,action,state)
    if not decision.allowed:raise PermissionError(decision.reason)
def system_principal()->Principal:return Principal('equiv-system',frozenset({Role.PLATFORM,Role.WAREHOUSE,Role.FINANCE,Role.OPERATIONS}))
def auditor(name:str)->Principal:return Principal(name,frozenset({Role.AUDITOR}))
