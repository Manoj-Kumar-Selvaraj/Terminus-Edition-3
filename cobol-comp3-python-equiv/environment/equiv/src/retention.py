from __future__ import annotations
from dataclasses import dataclass
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import os,stat

@dataclass(frozen=True)
class RetentionPolicy:
    report_days:int=90
    publication_days:int=365
    audit_days:int=2555
    quarantine_days:int=365
    def validate(self)->None:
        for name,value in self.__dict__.items():
            if value<=0:raise ValueError(f'{name} must be positive')
@dataclass(frozen=True)
class RetentionDecision:
    kind:str
    created_at:datetime
    expires_at:datetime
    expired:bool

def expiry(kind:str,created_at:datetime,policy:RetentionPolicy)->datetime:
    policy.validate();days={'report':policy.report_days,'publication':policy.publication_days,'audit':policy.audit_days,'quarantine':policy.quarantine_days}.get(kind)
    if days is None:raise ValueError(f'unknown retention kind {kind}')
    return created_at+timedelta(days=days)
def decision(kind:str,created_at:datetime,policy:RetentionPolicy,now:datetime|None=None)->RetentionDecision:
    now=now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:created_at=created_at.replace(tzinfo=timezone.utc)
    exp=expiry(kind,created_at,policy);return RetentionDecision(kind,created_at,exp,now>=exp)
def immutable(path:str|Path)->bool:
    mode=Path(path).stat().st_mode;return not bool(mode & stat.S_IWUSR)
def make_immutable(path:str|Path)->None:
    p=Path(path);p.chmod(p.stat().st_mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)
def assert_immutable(path:str|Path)->None:
    if not immutable(path):raise ValueError(f'{path} remains writable')
def eligible_for_delete(kind:str,path:str|Path,created_at:datetime,policy:RetentionPolicy,now:datetime|None=None)->bool:
    p=Path(path)
    if not p.exists():return False
    d=decision(kind,created_at,policy,now)
    if not d.expired:return False
    if kind in {'publication','audit'} and not immutable(p):return False
    return True
def retention_summary(policy:RetentionPolicy)->dict[str,int]:
    policy.validate();return {'report':policy.report_days,'publication':policy.publication_days,'audit':policy.audit_days,'quarantine':policy.quarantine_days}
