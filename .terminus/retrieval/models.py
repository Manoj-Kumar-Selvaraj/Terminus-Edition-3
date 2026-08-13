"""Typed interfaces shared by the retrieval engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class InvocationContext:
    """Authority/freshness envelope for one retrieval invocation."""

    stage_id: str
    role_id: str
    task_id: str | None = None
    task_commit: str | None = None
    control_plane_commit: str | None = None
    role_contract_hash: str | None = None
    packet_binding: str | None = None
    review_scope_hash: str | None = None
    ci_run_id: str | int | None = None
    policy_versions: Mapping[str, str] = field(default_factory=dict)
    allowed_evidence_classes: frozenset[str] | None = None
    excluded_evidence_classes: frozenset[str] = frozenset()
    allowed_sensitivities: frozenset[str] | None = None


@dataclass(frozen=True)
class RetrievalQuery:
    """One exact/lexical/vector/hybrid retrieval request."""

    text: str = ""
    mode: str = "auto"
    limit: int = 10
    source_kinds: tuple[str, ...] = ()
    evidence_classes: tuple[str, ...] = ()
    source_paths: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    section_terms: tuple[str, ...] = ()
    exact_phrase: str | None = None


@dataclass(frozen=True)
class SearchResult:
    """Authorized retrieval result with component and fused scores."""

    chunk_id: str
    document_id: str
    content: str
    metadata: Mapping[str, Any]
    exact_score: float = 0.0
    lexical_score: float = 0.0
    vector_score: float = 0.0
    fused_score: float = 0.0


@dataclass(frozen=True)
class RawChunk:
    """Structural content unit emitted before metadata binding."""

    content: str
    chunk_type: str
    structural_locator: str
    ordinal: int
    section_path: tuple[str, ...] = ()
    symbol: str | None = None
    line_start: int | None = None
    line_end: int | None = None
