"""Approved local cache and retrieval for human-writing calibration evidence.

External source text may exist only in this ignored local cache. Task-time packs receive
source IDs and structural observations, not raw source text.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Iterable


class CorpusCacheError(ValueError):
    """Raised when a cache record violates dataset or provenance policy."""


class HumanWritingCorpusCache:
    """Store and retrieve approved calibration records from a local SQLite cache."""

    schema_version = "1.0"

    def __init__(self, root: Path, path: Path | None = None):
        self.root = root.resolve()
        self.path = (
            path
            if path is not None
            else self.root / ".terminus" / "cache" / "human-writing.sqlite3"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        registry_path = self.root / ".terminus" / "human_writing" / "dataset_registry.json"
        self.registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.datasets = {dataset["id"]: dataset for dataset in self.registry["datasets"]}
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
                    PRIMARY KEY (dataset_id, source_id)
                );
                CREATE INDEX IF NOT EXISTS idx_hw_domain ON samples(domain);
                CREATE INDEX IF NOT EXISTS idx_hw_artifact ON samples(artifact_type);
                CREATE INDEX IF NOT EXISTS idx_hw_role ON samples(role_signal);
                """
            )

    def upsert(self, record: dict[str, Any]) -> None:
        """Insert one approved record after dataset and attribution validation."""
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
                f"{dataset_id} is already local structural metadata and must not be cached"
            )

        retained_text = record.get("text")
        source_url = record.get("source_url")
        author = record.get("author")
        author_url = record.get("author_url")
        if retained_text:
            if not source_url:
                raise CorpusCacheError("retained source text requires source_url")
            if dataset_id == "h4-stack-exchange-preferences":
                if not author or not author_url:
                    raise CorpusCacheError(
                        "retained Stack Exchange text requires author and author_url"
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
            hashlib.sha256(str(retained_text).encode()).hexdigest()
            if retained_text
            else record.get("text_sha256")
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO samples (
                    dataset_id, source_id, source_url, domain, artifact_type,
                    role_signal, structural_summary, retained_text, text_sha256,
                    license, author, author_url, vector_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_id, source_id) DO UPDATE SET
                    source_url=excluded.source_url,
                    domain=excluded.domain,
                    artifact_type=excluded.artifact_type,
                    role_signal=excluded.role_signal,
                    structural_summary=excluded.structural_summary,
                    retained_text=excluded.retained_text,
                    text_sha256=excluded.text_sha256,
                    license=excluded.license,
                    author=excluded.author,
                    author_url=excluded.author_url,
                    vector_json=excluded.vector_json
                """,
                (
                    dataset_id,
                    str(record["source_id"]),
                    source_url,
                    str(record["domain"]),
                    str(record["artifact_type"]),
                    str(record["role_signal"]),
                    str(record["structural_summary"]),
                    retained_text,
                    text_sha,
                    dataset["license"],
                    author,
                    author_url,
                    vector_json,
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
    ) -> list[dict[str, Any]]:
        """Rank by lexical/domain relevance plus optional precomputed vectors."""
        if limit <= 0:
            return []
        query_tokens = _tokens(query)
        artifact_set = {value.lower() for value in artifact_types}
        excluded = set(exclude_source_keys)
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM samples").fetchall()

        ranked: list[tuple[float, str, dict[str, Any]]] = []
        for row in rows:
            key = f"{row['dataset_id']}:{row['source_id']}"
            if key in excluded:
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
            public = {
                "dataset_id": row["dataset_id"],
                "source_id": row["source_id"],
                "source_url": row["source_url"],
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
            {
                "source_key": f"{row['dataset_id']}:{row['source_id']}",
                "text": row["retained_text"],
            }
            for row in rows
            if f"{row['dataset_id']}:{row['source_id']}" in wanted
        ]

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
