"""Authorization-first exact, lexical, vector, and hybrid retrieval."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from .embeddings import EmbeddingProvider, HashingEmbedder, cosine_similarity
from .models import InvocationContext, RetrievalQuery, SearchResult
from .policy import RetrievalPolicy
from .store import RetrievalStore

_TOKEN = re.compile(r"[A-Za-z0-9_./:-]+")
_VALID_MODES = {"auto", "exact", "lexical", "vector", "hybrid"}


class RetrievalEngine:
    """Run ranking only after stage/role/packet/freshness authorization."""

    def __init__(
        self,
        root: Path,
        store: RetrievalStore,
        *,
        policy: RetrievalPolicy | None = None,
        embedder: EmbeddingProvider | None = None,
    ):
        self.root = root.resolve()
        self.store = store
        self.policy = policy or RetrievalPolicy(self.root)
        self.embedder = embedder or HashingEmbedder()

    def retrieve(
        self, context: InvocationContext, query: RetrievalQuery
    ) -> list[SearchResult]:
        context = self.policy.validate_context(context)
        if query.mode not in _VALID_MODES:
            raise ValueError(f"invalid retrieval mode: {query.mode}")
        if query.limit <= 0:
            return []

        self._validate_query_filters(query)
        rows = self.store.candidate_rows(
            source_kinds=query.source_kinds,
            evidence_classes=query.evidence_classes,
            source_paths=query.source_paths,
            symbols=query.symbols,
            section_terms=query.section_terms,
        )
        authorized = [
            row
            for row in rows
            if self.policy.authorize_chunk(row["metadata"], context).allowed
        ]
        mode = self._resolve_mode(context, query.mode)

        authority_hash = self._authority_hash(context)
        query_hash = self._query_hash(query, mode)
        candidate_set_hash = self._candidate_set_hash(authorized)
        cache_key = self._sha(authority_hash, query_hash, candidate_set_hash)
        cached = self.store.get_cached_result(cache_key)
        if cached is not None:
            cached_rows = self.store.rows_by_ids(cached)
            still_authorized = [
                row
                for row in cached_rows
                if self.policy.authorize_chunk(row["metadata"], context).allowed
            ]
            if len(still_authorized) == len(cached_rows) == len(cached):
                return [
                    SearchResult(
                        chunk_id=row["chunk_id"],
                        document_id=row["document_id"],
                        content=row["content"],
                        metadata=row["metadata"],
                        fused_score=1.0 / (index + 1.0),
                    )
                    for index, row in enumerate(still_authorized[: query.limit])
                ]

        if mode == "exact":
            results = self._exact_results(authorized, query)
        elif mode == "lexical":
            results = self._lexical_results(authorized, query)
        elif mode == "vector":
            results = self._vector_results(authorized, query)
        else:
            results = self._hybrid_results(authorized, query)

        results = results[: query.limit]
        self.store.put_cached_result(
            cache_key,
            authority_hash,
            query_hash,
            [result.chunk_id for result in results],
        )
        return results

    def context_bundle(
        self,
        context: InvocationContext,
        query: RetrievalQuery,
        *,
        max_chars: int = 30000,
    ) -> dict[str, Any]:
        """Return exact-read requirements plus bounded authorized retrieved context."""
        if max_chars < 0:
            raise ValueError("max_chars must be non-negative")
        context = self.policy.validate_context(context)
        results = self.retrieve(context, query)
        included: list[dict[str, Any]] = []
        used = 0
        for result in results:
            remaining = max_chars - used
            if remaining <= 0:
                break
            content = result.content
            truncated = len(content) > remaining
            if truncated:
                content = content[:remaining]
            item = {
                "chunk_id": result.chunk_id,
                "source_path": result.metadata.get("source_path"),
                "source_kind": result.metadata.get("source_kind"),
                "evidence_class": result.metadata.get("evidence_class"),
                "structural_locator": result.metadata.get("structural_locator"),
                "content_hash": result.metadata.get("content_hash"),
                "content": content,
                "score": result.fused_score
                or result.lexical_score
                or result.vector_score
                or result.exact_score,
            }
            if truncated:
                item["truncated"] = True
            included.append(item)
            used += len(content)
            if truncated:
                break
        return {
            "stage_id": context.stage_id,
            "role_id": context.role_id,
            "retrieval_mode": self.policy.retrieval_mode(context.stage_id),
            "mandatory_exact_reads": list(
                self.policy.mandatory_exact_paths(context.stage_id)
            ),
            "authorized_evidence_classes": sorted(
                self.policy.authorized_evidence_classes(context)
            ),
            "retrieved_context": included,
            "retrieved_chars": used,
        }

    def _resolve_mode(self, context: InvocationContext, requested: str) -> str:
        stage_mode = self.policy.retrieval_mode(context.stage_id)
        if stage_mode == "EXACT_ONLY":
            return "exact"
        if stage_mode == "EXTERNAL_BOUND":
            return "exact"
        if requested != "auto":
            return requested
        return "hybrid"

    def _validate_query_filters(self, query: RetrievalQuery) -> None:
        unknown_sources = set(query.source_kinds) - self.policy.source_kinds
        if unknown_sources:
            raise ValueError(f"unknown source kinds: {sorted(unknown_sources)}")
        unknown_evidence = set(query.evidence_classes) - self.policy.evidence_classes
        if unknown_evidence:
            raise ValueError(f"unknown evidence classes: {sorted(unknown_evidence)}")

    def _exact_results(
        self, rows: Sequence[dict[str, Any]], query: RetrievalQuery
    ) -> list[SearchResult]:
        scored: list[SearchResult] = []
        text = query.text.strip().lower()
        phrase = (query.exact_phrase or "").strip().lower()
        tokens = [token.lower() for token in _TOKEN.findall(text)]
        has_text_constraint = bool(text or phrase)
        for row in rows:
            metadata = row["metadata"]
            haystacks = [
                row["content"].lower(),
                str(metadata.get("source_path", "")).lower(),
                str(metadata.get("symbol", "")).lower(),
                " / ".join(metadata.get("section_path", [])).lower(),
            ]
            combined = "\n".join(haystacks)
            if phrase and phrase not in combined:
                continue
            score = 1.0 if not has_text_constraint else 0.0
            if text and text in combined:
                score += 4.0
            score += sum(1.0 for token in set(tokens) if token in combined)
            if has_text_constraint and score <= 0:
                continue
            scored.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    content=row["content"],
                    metadata=metadata,
                    exact_score=score,
                    fused_score=score,
                )
            )
        scored.sort(
            key=lambda item: (
                -item.exact_score,
                str(item.metadata.get("source_path", "")),
                int(item.metadata.get("ordinal", 0)),
                item.chunk_id,
            )
        )
        return scored

    def _lexical_results(
        self, rows: Sequence[dict[str, Any]], query: RetrievalQuery
    ) -> list[SearchResult]:
        if not query.text.strip():
            return self._exact_results(rows, query)
        ranking = self.store.lexical_search(
            query.text,
            [row["chunk_id"] for row in rows],
            max(query.limit * 4, query.limit),
        )
        return self._materialize_ranked(rows, ranking, component="lexical")

    def _vector_results(
        self, rows: Sequence[dict[str, Any]], query: RetrievalQuery
    ) -> list[SearchResult]:
        if not query.text.strip():
            return self._exact_results(rows, query)
        query_vector = self.embedder.embed([query.text])[0]
        ranked: list[tuple[str, float]] = []
        missing_rows: list[dict[str, Any]] = []
        missing_texts: list[str] = []
        vectors: dict[str, list[float]] = {}
        for row in rows:
            metadata = row["metadata"]
            vector = self.store.get_embedding(
                row["chunk_id"],
                self.embedder.name,
                self.embedder.version,
                metadata["content_hash"],
            )
            if vector is None:
                missing_rows.append(row)
                missing_texts.append(row["content"])
            else:
                vectors[row["chunk_id"]] = vector
        if missing_rows:
            generated = self.embedder.embed(missing_texts)
            for row, vector in zip(missing_rows, generated, strict=True):
                vectors[row["chunk_id"]] = vector
                self.store.put_embedding(
                    row["chunk_id"],
                    self.embedder.name,
                    self.embedder.version,
                    row["metadata"]["content_hash"],
                    vector,
                )
        for row in rows:
            score = cosine_similarity(query_vector, vectors[row["chunk_id"]])
            if score > 0.0:
                ranked.append((row["chunk_id"], score))
        ranked.sort(key=lambda item: (-item[1], item[0]))
        return self._materialize_ranked(rows, ranked, component="vector")

    def _hybrid_results(
        self, rows: Sequence[dict[str, Any]], query: RetrievalQuery
    ) -> list[SearchResult]:
        exact = self._exact_results(rows, query)
        lexical = self._lexical_results(rows, query)
        vector = self._vector_results(rows, query)
        rankings = [exact, lexical, vector]
        weights = [1.2, 1.0, 0.8]
        fused: defaultdict[str, float] = defaultdict(float)
        components: dict[str, tuple[float, float, float]] = {}
        for weight, ranking in zip(weights, rankings, strict=True):
            for rank, result in enumerate(ranking, start=1):
                fused[result.chunk_id] += weight / (60.0 + rank)
                old = components.get(result.chunk_id, (0.0, 0.0, 0.0))
                components[result.chunk_id] = (
                    max(old[0], result.exact_score),
                    max(old[1], result.lexical_score),
                    max(old[2], result.vector_score),
                )
        row_map = {row["chunk_id"]: row for row in rows}
        ordered = sorted(fused, key=lambda chunk_id: (-fused[chunk_id], chunk_id))
        output: list[SearchResult] = []
        for chunk_id in ordered:
            row = row_map[chunk_id]
            exact_score, lexical_score, vector_score = components[chunk_id]
            output.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=row["document_id"],
                    content=row["content"],
                    metadata=row["metadata"],
                    exact_score=exact_score,
                    lexical_score=lexical_score,
                    vector_score=vector_score,
                    fused_score=fused[chunk_id],
                )
            )
        return output

    @staticmethod
    def _materialize_ranked(
        rows: Sequence[dict[str, Any]],
        ranking: Sequence[tuple[str, float]],
        *,
        component: str,
    ) -> list[SearchResult]:
        row_map = {row["chunk_id"]: row for row in rows}
        results: list[SearchResult] = []
        for chunk_id, score in ranking:
            row = row_map.get(chunk_id)
            if row is None:
                continue
            kwargs: dict[str, float] = {f"{component}_score": score, "fused_score": score}
            results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=row["document_id"],
                    content=row["content"],
                    metadata=row["metadata"],
                    **kwargs,
                )
            )
        return results

    def _authority_hash(self, context: InvocationContext) -> str:
        payload = {
            "stage_id": context.stage_id,
            "role_id": context.role_id,
            "task_id": context.task_id,
            "task_commit": context.task_commit,
            "control_plane_commit": context.control_plane_commit,
            "role_contract_hash": context.role_contract_hash,
            "packet_binding": context.packet_binding,
            "review_scope_hash": context.review_scope_hash,
            "ci_run_id": str(context.ci_run_id) if context.ci_run_id is not None else None,
            "policy_versions": dict(sorted(context.policy_versions.items())),
            "allowed_evidence_classes": sorted(context.allowed_evidence_classes or ()),
            "excluded_evidence_classes": sorted(context.excluded_evidence_classes),
            "allowed_sensitivities": sorted(context.allowed_sensitivities or ()),
            "visibility_version": self.policy.visibility_registry.get("visibility_version"),
            "metadata_version": self.policy.metadata_registry.get("metadata_contract_version"),
        }
        return self._sha(json.dumps(payload, sort_keys=True, separators=(",", ":")))

    @staticmethod
    def _query_hash(query: RetrievalQuery, mode: str) -> str:
        payload = {
            "text": query.text,
            "mode": mode,
            "limit": query.limit,
            "source_kinds": list(query.source_kinds),
            "evidence_classes": list(query.evidence_classes),
            "source_paths": list(query.source_paths),
            "symbols": list(query.symbols),
            "section_terms": list(query.section_terms),
            "exact_phrase": query.exact_phrase,
        }
        return RetrievalEngine._sha(
            json.dumps(payload, sort_keys=True, separators=(",", ":"))
        )

    @staticmethod
    def _candidate_set_hash(rows: Sequence[dict[str, Any]]) -> str:
        """Bind cached rankings to the actual authorized pre-rank candidate pool."""
        identities = sorted(
            (
                str(row["chunk_id"]),
                str(row["metadata"].get("content_hash", "")),
            )
            for row in rows
        )
        return RetrievalEngine._sha(
            json.dumps(identities, separators=(",", ":"))
        )

    @staticmethod
    def _sha(*parts: str) -> str:
        digest = hashlib.sha256()
        for part in parts:
            digest.update(part.encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()
