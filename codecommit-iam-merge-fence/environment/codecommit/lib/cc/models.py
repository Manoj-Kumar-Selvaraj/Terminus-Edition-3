from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Principal:
    name: str
    policies: list[str]
    roles: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, name: str, raw: dict[str, Any]) -> "Principal":
        return cls(
            name=name,
            policies=list(raw.get("policies") or []),
            roles=list(raw.get("roles") or []),
        )


@dataclass
class AuthContext:
    principal: str
    action: str
    resource_arn: str
    reference: str
    mfa: bool
    source_ip: str

    def as_eval_map(self) -> dict[str, Any]:
        return {
            "aws:MultiFactorAuthPresent": self.mfa,
            "aws:SourceIp": self.source_ip,
            "codecommit:References": self.reference,
        }


@dataclass
class PullRequest:
    pr_id: int
    repo: str
    source: str
    dest: str
    source_commit: str
    author: str
    status: str
    approvals: list[str] = field(default_factory=list)
    merged_commit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditEvent:
    principal: str
    action: str
    resource: str
    reference: str
    allowed: bool
    reason: str
    source_ip: str
    mfa: bool

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutboxItem:
    event_id: str
    repo: str
    ref: str
    commit: str
    pipeline: str
    webhook_id: str
    status: str
    attempts: int = 0
    last_error: str | None = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)
