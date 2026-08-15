from __future__ import annotations
from dataclasses import dataclass
from .models import RunState

ALLOWED={
 RunState.CREATED:{RunState.PROCESSING},
 RunState.PROCESSING:{RunState.RECONCILING,RunState.HELD},
 RunState.RECONCILING:{RunState.READY,RunState.HELD},
 RunState.READY:{RunState.PUBLISHED,RunState.HELD},
 RunState.HELD:{RunState.PROCESSING,RunState.RECONCILING},
 RunState.PUBLISHED:set(),
}
@dataclass(frozen=True)
class Transition:
    before:RunState
    after:RunState
    reason:str

def can_transition(before:RunState,after:RunState)->bool:return after in ALLOWED.get(before,set())
def require_transition(before:RunState,after:RunState)->None:
    if not can_transition(before,after):raise ValueError(f"invalid run transition {before.value}->{after.value}")
def transition_path(start:RunState,end:RunState)->list[RunState]:
    if start==end:return [start]
    queue=[(start,[start])];seen={start}
    while queue:
        state,path=queue.pop(0)
        for nxt in ALLOWED.get(state,set()):
            if nxt==end:return path+[nxt]
            if nxt not in seen:seen.add(nxt);queue.append((nxt,path+[nxt]))
    return []
def terminal(state:RunState)->bool:return state==RunState.PUBLISHED
def resumable(state:RunState)->bool:return state in {RunState.PROCESSING,RunState.HELD,RunState.RECONCILING}
def publication_allowed(state:RunState)->bool:return state==RunState.READY
def explain_invalid(before:RunState,after:RunState)->str:
    if can_transition(before,after):return ""
    if before==RunState.PUBLISHED:return "published generation is immutable"
    if after==RunState.PUBLISHED and before!=RunState.READY:return "publication requires READY reconciliation"
    if after==RunState.READY and before!=RunState.RECONCILING:return "READY requires reconciliation phase"
    return f"transition from {before.value} to {after.value} is not declared"
class RunLifecycle:
    def __init__(self,state:RunState=RunState.CREATED):self.state=state;self.history=[state]
    def move(self,after:RunState,reason:str="")->Transition:
        before=self.state;require_transition(before,after);self.state=after;self.history.append(after);return Transition(before,after,reason)
    def held(self)->bool:return self.state==RunState.HELD
    def complete(self)->bool:return terminal(self.state)
    def may_resume(self)->bool:return resumable(self.state)
    def path(self)->tuple[str,...]:return tuple(s.value for s in self.history)
