"""Approved local cache and retrieval for human-writing calibration evidence.

Raw source text is local-only. Task-time packs receive source IDs, provenance and
structural observations, never the retained source body.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Iterable


class CorpusCacheError(ValueError):
    """Raised when a cache record violates dataset, role or provenance policy."""


class HumanWritingCorpusCache:
    """Store and retrieve approved calibration records from a local SQLite cache."""

    schema_version = "1.1"

    def __init__(self, root: Path, path: Path | None = None):
        self.root = root.resolve()
        self.path = path if path is not None else (
            self.root / ".terminus" / "cache" / "human-writing.sqlite3"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        registry_path = self.root / ".terminus" / "human_writing" / "dataset_registry.json"
        self.registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.datasets = {dataset["id"]: dataset for dataset in self.registry["datasets"]}
        self.cache_policy = self.registry.get("cache_policy", {})
        self._fts_enabled = False
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS samples (
                    dataset_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_url TEXT,
                    source_revision TEXT,
                    source_site TEXT,
                    annotation_kind TEXT,
                    domain TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    role_signal TEXT NOT NULL,
                    structural_summary TEXT NOT NULL,
                    retained_text TEXT,
                    text_sha256 TEXT,
                    license TEXT NOT NULL,
                    author TEXT,
                    author_url TEXT,
                    vector_json TEXT,
                    provenance_json TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY (dataset_id, source_id)
                );
                CREATE INDEX IF NOT EXISTS idx_hw_domain ON samples(domain);
                CREATE INDEX IF NOT EXISTS idx_hw_artifact ON samples(artifact_type);
                CREATE INDEX IF NOT EXISTS idx_hw_role ON samples(role_signal);
                CREATE INDEX IF NOT EXISTS idx_hw_dataset ON samples(dataset_id);
                """
            )
            self._migrate_columns(conn)
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS samples_fts USING fts5("
                    "source_key UNINDEXED, domain, artifact_type, structural_summary)"
                )
                self._fts_enabled = True
            except sqlite3.OperationalError:
                self._fts_enabled = False

    @staticmethod
    def _migrate_columns(conn: sqlite3.Connection) -> None:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(samples)")}
        additions = {
            "source_revision": "TEXT",
            "source_site": "TEXT",
            "annotation_kind": "TEXT",
            "provenance_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for name, declaration in additions.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE samples ADD COLUMN {name} {declaration}")

    def upsert(self, record: dict[str, Any]) -> None:
        """Insert one approved record after dataset, role and provenance validation."""
        required = {
            "dataset_id",
            "source_id",
            "domain",
            "artifact_type",
            "role_signal",
            "structural_summary",
        }
        missing = sorted(required - record.keys())
        if missing:
            raise CorpusCacheError(f"missing cache fields: {missing}")

        dataset_id = str(record["dataset_id"])
        dataset = self.datasets.get(dataset_id)
        if not dataset or dataset.get("enabled") is not True:
            raise CorpusCacheError(f"dataset is disabled or unknown: {dataset_id}")
        if dataset.get("content_mode") == "local_structural_catalog":
            raise CorpusCacheError(
                f"{dataset_id} is local structural metadata and must not be cached"
            )

        role_signal = str(record["role_signal"])
        allowed_roles = set(dataset.get("allowed_roles", []))
        requested_roles = {"writer", "reviewer"} if role_signal == "both" else {role_signal}
        if not requested_roles or not requested_roles <= {"writer", "reviewer"}:
            raise CorpusCacheError(f"invalid role_signal: {role_signal}")
        if not requested_roles <= allowed_roles:
            raise CorpusCacheError(
                f"dataset {dataset_id} is not authorized for roles {sorted(requested_roles)}"
            )

        if self.cache_policy.get("require_source_revision_for_external_cache") is True:
            if not record.get("source_revision"):
                raise CorpusCacheError("external cache record requires source_revision")

        for field in dataset.get("provenance_requirements", []):
            if field == "source_question_id" and record.get("source_id"):
                continue
            if not record.get(field):
                raise CorpusCacheError(
                    f"dataset {dataset_id} requires provenance field: {field}"
                )

        retained_text = record.get("text")
        if retained_text:
            for field in dataset.get("retained_text_requirements", []):
                if not record.get(field):
                    raise CorpusCacheError(
                        f"retained {dataset_id} text requires field: {field}"
                    )

        vector = record.get("vector")
        if vector is not None:
            if not isinstance(vector, list) or not vector or not all(
                isinstance(value, (int, float)) for value in vector
            ):
                raise CorpusCacheError("vector must be a non-empty numeric list")
            vector_json = json.dumps([float(value) for value in vector])
        else:
            vector_json = None

        text_sha = (
            hashlib.sha256(str(retained_text).encode("utf-8")).hexdigest()
            if retained_text
            else record.get("text_sha256")
        )
        provenance = {
            key: value
            for key, value in record.items()
            if key
            not in {
                "text",
                "vector",
                "structural_summary",
            }
        }
        values = (
            dataset_id,
            str(record["source_id"]),
            record.get("source_url"),
            record.get("source_revision"),
            record.get("source_site"),
            record.get("annotation_kind"),
            str(record["domain"]),
            str(record["artifact_type"]),
            role_signal,
            str(record["structural_summary"]),
            retained_text,
            text_sha,
            dataset["license"],
            record.get("author"),
            record.get("author_url"),
            vector_json,
            json.dumps(provenance, sort_keys=True),
        )
        source_key = f"{dataset_id}:{record['source_id']}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO samples (
                    dataset_id, source_id, source_url, source_revision, source_site,
                    annotation_kind, domain, artifact_type, role_signal,
                    structural_summary, retained_text, text_sha256, license, author,
                    author_url, vector_json, provenance_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_id, source_id) DO UPDATE SET
                    source_url=excluded.source_url,
                    source_revision=excluded.source_revision,
                    source_site=excluded.source_site,
                    annotation_kind=excluded.annotation_kind,
                    domain=excluded.domain,
                    artifact_type=excluded.artifact_type,
                    role_signal=excluded.role_signal,
                    structural_summary=excluded.structural_summary,
                    retained_text=excluded.retained_text,
                    text_sha256=excluded.text_sha256,
                    license=excluded.license,
                    author=excluded.author,
                    author_url=excluded.author_url,
                    vector_json=excluded.vector_json,
                    provenance_json=excluded.provenance_json
                """,
                values,
            )
            if self._fts_enabled:
                conn.execute("DELETE FROM samples_fts WHERE source_key = ?", (source_key,))
                conn.execute(
                    "INSERT INTO samples_fts(source_key, domain, artifact_type, structural_summary) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        source_key,
                        str(record["domain"]),
                        str(record["artifact_type"]),
                        str(record["structural_summary"]),
                    ),
                )

    def search(
        self,
        query: str,
        *,
        role_signal: str | None = None,
        artifact_types: Iterable[str] = (),
        exclude_source_keys: Iterable[str] = (),
        query_vector: list[float] | None = None,
        limit: int = 12,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        """Rank bounded policy-authorized candidates by lexical/domain/vector relevance."""
        if limit <= 0:
            return []
        if role_signal not in {None, "writer", "reviewer"}:
            raise CorpusCacheError("search role_signal must be writer or reviewer")

        minimum = (
            float(min_score)
            if min_score is not None
            else float(self.cache_policy.get("minimum_relevance_score", 0.0))
        )
        max_candidates = int(self.cache_policy.get("maximum_prefilter_candidates", 500))
        query_tokens = _tokens(query)
        artifact_set = {value.lower() for value in artifact_types}
        excluded = set(exclude_source_keys)

        with self._connect() as conn:
            rows = self._candidate_rows(
                conn,
                query_tokens=query_tokens,
                role_signal=role_signal,
                artifact_set=artifact_set,
                max_candidates=max_candidates,
            )

        ranked: list[tuple[float, str, dict[str, Any]]] = []
        for row in rows:
            key = f"{row['dataset_id']}:{row['source_id']}"
            if key in excluded:
                continue
            dataset = self.datasets.get(row["dataset_id"], {})
            if dataset.get("enabled") is not True:
                continue
            if role_signal and role_signal not in set(dataset.get("allowed_roles", [])):
                continue
            if role_signal and row["role_signal"] not in {role_signal, "both"}:
                continue
            if artifact_set and row["artifact_type"].lower() not in artifact_set:
                continue

            haystack = " ".join(
                [row["domain"], row["artifact_type"], row["structural_summary"]]
            )
            sample_tokens = _tokens(haystack)
            lexical = _jaccard(query_tokens, sample_tokens)
            domain_overlap = len(query_tokens & _tokens(row["domain"]))
            domain_score = min(1.0, domain_overlap / 3.0)
            vector_score = 0.0
            if query_vector is not None and row["vector_json"]:
                vector_score = max(
                    0.0,
                    _cosine(
                        [float(value) for value in query_vector],
                        json.loads(row["vector_json"]),
                    ),
                )
                score = 0.50 * lexical + 0.30 * domain_score + 0.20 * vector_score
            else:
                score = 0.625 * lexical + 0.375 * domain_score
            if score < minimum:
                continue
            public = {
                "dataset_id": row["dataset_id"],
                "source_id": row["source_id"],
                "source_url": row["source_url"],
                "source_revision": row["source_revision"],
                "domain": row["domain"],
                "artifact_type": row["artifact_type"],
                "role_signal": row["role_signal"],
                "structural_summary": row["structural_summary"],
                "text_sha256": row["text_sha256"],
                "license": row["license"],
                "score": round(score, 6),
            }
            ranked.append((-score, key, public))
        ranked.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in ranked[:limit]]

    def _candidate_rows(
        self,
        conn: sqlite3.Connection,
        *,
        query_tokens: set[str],
        role_signal: str | None,
        artifact_set: set[str],
        max_candidates: int,
    ) -> list[sqlite3.Row]:
        source_keys: list[str] = []
        if self._fts_enabled and query_tokens:
            expression = " OR ".join(f'"{token}"' for token in sorted(query_tokens))
            try:
                source_keys = [
                    row[0]
                    for row in conn.execute(
                        "SELECT source_key FROM samples_fts WHERE samples_fts MATCH ? LIMIT ?",
                        (expression, max_candidates),
                    )
                ]
            except sqlite3.OperationalError:
                source_keys = []
        if source_keys:
            placeholders = ",".join("?" for _ in source_keys)
            return conn.execute(
                "SELECT * FROM samples WHERE (dataset_id || ':' || source_id) IN ("
                + placeholders
                + ")",
                source_keys,
            ).fetchall()

        clauses: list[str] = []
        params: list[Any] = []
        if role_signal:
            clauses.append("role_signal IN (?, 'both')")
            params.append(role_signal)
        if artifact_set:
            placeholders = ",".join("?" for _ in artifact_set)
            clauses.append(f"LOWER(artifact_type) IN ({placeholders})")
            params.extend(sorted(artifact_set))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(max_candidates)
        return conn.execute(
            "SELECT * FROM samples" + where + " ORDER BY dataset_id, source_id LIMIT ?",
            params,
        ).fetchall()

    def retained_texts(self, source_keys: Iterable[str]) -> list[dict[str, str]]:
        """Return raw local-only texts solely for contamination analysis."""
        wanted = set(source_keys)
        if not wanted:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT dataset_id, source_id, retained_text FROM samples "
                "WHERE retained_text IS NOT NULL"
            ).fetchall()
        return [
            {"source_key": f"{row['dataset_id']}:{row['source_id']}", "text": row["retained_text"]}
            for row in rows
            if f"{row['dataset_id']}:{row['source_id']}" in wanted
        ]

    def retained_source_keys(self, source_keys: Iterable[str]) -> set[str]:
        return {item["source_key"] for item in self.retained_texts(source_keys)}

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            by_dataset = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT dataset_id, COUNT(*) FROM samples GROUP BY dataset_id"
                )
            }
        return {
            "schema_version": self.schema_version,
            "path": str(self.path),
            "sample_count": total,
            "by_dataset": by_dataset,
            "fts_enabled": self._fts_enabled,
        }


def _tokens(value: str) -> set[str]:
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return {token for token in normalized.split() if len(token) >= 2}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
