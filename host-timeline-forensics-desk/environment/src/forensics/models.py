"""Typed contracts shared by API, worker, lab, and reporting modules."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .canonical import normalize_case_id, normalize_endpoint_id, normalize_source_id


class SourceMode(StrEnum):
    LIVE = "live"
    OFFLINE = "offline"


class SourceDisposition(StrEnum):
    REQUESTED = "requested"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CaseState(StrEnum):
    OPEN = "open"
    HOLD = "hold"
    CLOSED = "closed"


class EvidenceTrait(StrEnum):
    NORMAL = "normal"
    RECOVERED = "recovered"
    CORRUPT = "corrupt"
    INCOMPLETE = "incomplete"
    SYNTHETIC = "synthetic"


class ActorContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    actor_id: str = Field(min_length=1, max_length=96)
    tenant_id: str = Field(min_length=1, max_length=96)
    roles: frozenset[str] = frozenset()
    case_ids: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()


class SourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint_id: str = Field(min_length=3, max_length=96)
    source_id: str = Field(min_length=2, max_length=96)
    mode: SourceMode
    artifact_families: list[str] = Field(min_length=1, max_length=40)
    byte_limit: int = Field(gt=0)
    deadline: datetime
    required: bool = True

    @field_validator("endpoint_id")
    @classmethod
    def endpoint_identity(cls, value: str) -> str:
        return normalize_endpoint_id(value)

    @field_validator("source_id")
    @classmethod
    def source_identity(cls, value: str) -> str:
        return normalize_source_id(value)


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    idempotency_key: str = Field(min_length=1, max_length=160)
    policy_revision: str = Field(min_length=1, max_length=96)
    inventory_generation: int = Field(ge=1)
    sources: list[SourceRequest] = Field(min_length=1, max_length=200)
    requested_by: str = Field(min_length=1, max_length=96)

    @field_validator("case_id")
    @classmethod
    def case_identity(cls, value: str) -> str:
        return normalize_case_id(value)


class PlanView(BaseModel):
    plan_id: str
    case_id: str
    policy_revision: str
    plan_digest: str
    state: str
    item_count: int
    created_at: datetime


class CollectionEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    delivery_id: str
    case_id: str
    endpoint_id: str
    source_id: str
    plan_id: str
    collection_item_id: str
    attempt: int
    status: SourceDisposition
    occurred_at: datetime
    payload_digest: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class EvidenceManifestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    case_id: str
    endpoint_id: str
    source_id: str
    plan_id: str
    item_id: str
    attempt: int
    digest: str
    byte_length: int = Field(ge=0)
    captured_at: datetime
    traits: list[EvidenceTrait] = Field(default_factory=list)
    source_path: str = Field(min_length=1, max_length=512)


class CustodyTransfer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transfer_id: str
    evidence_id: str
    from_actor: str
    to_actor: str
    reason: str = Field(min_length=1, max_length=512)
    transferred_at: datetime


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    requested_by: str
    format: str = Field(default="manifest-v1", pattern="^manifest-v1$")
    include_timeline: bool = True
    include_unavailable: bool = True
