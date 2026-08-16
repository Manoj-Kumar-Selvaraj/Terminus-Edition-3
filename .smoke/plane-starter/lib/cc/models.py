"""Typed views over the JSON documents the control plane stores and evaluates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cc.util import as_bool, as_list


@dataclass(frozen=True)
class Statement:
    """One IAM-style statement from an attached policy document."""

    sid: str
    effect: str
    actions: tuple[str, ...]
    resources: tuple[str, ...]
    condition: dict[str, Any]
    policy_id: str

    @property
    def is_deny(self) -> bool:
        return self.effect.lower() == "deny"

    @property
    def is_allow(self) -> bool:
        return self.effect.lower() == "allow"

    @classmethod
    def from_dict(cls, body: dict[str, Any], policy_id: str, index: int) -> "Statement":
        condition = body.get("Condition") or {}
        if not isinstance(condition, dict):
            condition = {}
        return cls(
            sid=str(body.get("Sid") or f"{policy_id}#{index}"),
            effect=str(body.get("Effect") or "Allow"),
            actions=tuple(str(item) for item in as_list(body.get("Action"))),
            resources=tuple(str(item) for item in as_list(body.get("Resource"))),
            condition=condition,
            policy_id=policy_id,
        )


@dataclass(frozen=True)
class RequestContext:
    """Request keys an evaluated condition block may inspect."""

    principal: str
    action: str
    repo: str
    ref: str | None = None
    source_ip: str | None = None
    mfa: bool | None = None

    def keys(self) -> dict[str, Any]:
        values: dict[str, Any] = {"aws:username": self.principal, "cc:Repository": self.repo}
        if self.ref is not None:
            values["codecommit:References"] = self.ref
        if self.source_ip is not None:
            values["aws:SourceIp"] = self.source_ip
        if self.mfa is not None:
            values["aws:MultiFactorAuthPresent"] = bool(self.mfa)
        return values


@dataclass(frozen=True)
class Decision:
    """Outcome of evaluating one request against a principal's policy set."""

    allowed: bool
    reason: str
    statement: str | None = None
    policy_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": "allow" if self.allowed else "deny",
            "reason": self.reason,
            "statement": self.statement,
            "policy": self.policy_id,
        }


@dataclass(frozen=True)
class Repository:
    """Catalog entry for one bare repository under ``var/repos``."""

    name: str
    arn: str
    default_branch: str
    protected_refs: tuple[str, ...] = ()
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arn": self.arn,
            "default_branch": self.default_branch,
            "protected_refs": list(self.protected_refs),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> "Repository":
        return cls(
            name=str(body["name"]),
            arn=str(body["arn"]),
            default_branch=str(body.get("default_branch") or "refs/heads/main"),
            protected_refs=tuple(str(item) for item in body.get("protected_refs") or []),
            description=str(body.get("description") or ""),
        )


@dataclass
class PullRequest:
    """Persistent pull-request record held in ``var/prs.json``."""

    pr_id: int
    repo: str
    source: str
    dest: str
    author: str
    source_commit: str
    base_commit: str
    status: str = "open"
    approvals: list[str] = field(default_factory=list)
    merged_commit: str | None = None
    merged_by: str | None = None
    created_at: str = ""
    title: str = ""

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    def as_dict(self) -> dict[str, Any]:
        return {
            "pr_id": self.pr_id,
            "repo": self.repo,
            "source": self.source,
            "dest": self.dest,
            "author": self.author,
            "source_commit": self.source_commit,
            "base_commit": self.base_commit,
            "status": self.status,
            "approvals": sorted(self.approvals),
            "merged_commit": self.merged_commit,
            "merged_by": self.merged_by,
            "created_at": self.created_at,
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> "PullRequest":
        return cls(
            pr_id=int(body["pr_id"]),
            repo=str(body["repo"]),
            source=str(body["source"]),
            dest=str(body["dest"]),
            author=str(body["author"]),
            source_commit=str(body.get("source_commit") or ""),
            base_commit=str(body.get("base_commit") or ""),
            status=str(body.get("status") or "open"),
            approvals=[str(item) for item in body.get("approvals") or []],
            merged_commit=body.get("merged_commit"),
            merged_by=body.get("merged_by"),
            created_at=str(body.get("created_at") or ""),
            title=str(body.get("title") or ""),
        )


@dataclass(frozen=True)
class ApprovalRule:
    """Destination rule that decides how many pool stamps a merge needs."""

    rule_id: str
    repo: str
    dest: str
    required: int
    pool: tuple[str, ...]

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> "ApprovalRule":
        return cls(
            rule_id=str(body.get("rule_id") or f"{body.get('repo')}:{body.get('dest')}"),
            repo=str(body.get("repo") or ""),
            dest=str(body.get("dest") or ""),
            required=int(body.get("required") or 0),
            pool=tuple(str(item) for item in body.get("pool") or []),
        )


@dataclass(frozen=True)
class PipelineBinding:
    """Repository and ref that start a named pipeline when delivered."""

    pipeline: str
    repo: str
    ref: str
    enabled: bool = True

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> "PipelineBinding":
        return cls(
            pipeline=str(body.get("pipeline") or ""),
            repo=str(body.get("repo") or ""),
            ref=str(body.get("ref") or ""),
            enabled=as_bool(body.get("enabled", True)),
        )


@dataclass(frozen=True)
class WebhookEndpoint:
    """Outbound endpoint that mirrors delivered pipeline events."""

    endpoint: str
    url: str
    pipelines: tuple[str, ...]
    max_attempts: int
    backoff_base_ticks: int
    reject_until_attempt: int
    enabled: bool
    sink: str

    def wants(self, pipeline: str) -> bool:
        return pipeline in self.pipelines

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> "WebhookEndpoint":
        return cls(
            endpoint=str(body.get("endpoint") or ""),
            url=str(body.get("url") or ""),
            pipelines=tuple(str(item) for item in body.get("pipelines") or []),
            max_attempts=int(body.get("max_attempts") or 1),
            backoff_base_ticks=int(body.get("backoff_base_ticks") or 1),
            reject_until_attempt=int(body.get("reject_until_attempt") or 0),
            enabled=as_bool(body.get("enabled", True)),
            sink=str(body.get("sink") or ""),
        )
