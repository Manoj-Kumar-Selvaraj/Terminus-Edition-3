"""SQLite-backed retrieval index, lexical search, and caches."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_TOKEN = re.compile(r"[A-Za-z0-9_./:-]+")


class RetrievalStore:
    """Local durable retrieval store with optional SQLite FTS5 acceleration."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.fts_available = False
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "RetrievalStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                source_uri TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_version TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                evidence_class TEXT NOT NULL,
                sensitivity TEXT NOT NULL,
                solver_visible INTEGER NOT NULL,
                task_id TEXT,
                task_commit TEXT,
                control_plane_commit TEXT,
                source_path TEXT,
                symbol TEXT,
                section_path TEXT,
                ordinal INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chunks_source_kind ON chunks(source_kind);
            CREATE INDEX IF NOT EXISTS idx_chunks_evidence_class ON chunks(evidence_class);
            CREATE INDEX IF NOT EXISTS idx_chunks_task ON chunks(task_id, task_commit);
            CREATE INDEX IF NOT EXISTS idx_chunks_control_plane ON chunks(control_plane_commit);
            CREATE TABLE IF NOT EXISTS parse_cache (
                cache_key TEXT PRIMARY KEY,
                source_version TEXT NOT NULL,
                strategy TEXT NOT NULL,
                chunker_version TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                chunks_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_parse_cache_source ON parse_cache(source_version, strategy, chunker_version);
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                provider_version TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                PRIMARY KEY(chunk_id, provider, provider_version)
            );
            CREATE TABLE IF NOT EXISTS retrieval_cache (
                cache_key TEXT PRIMARY KEY,
                authority_hash TEXT NOT NULL,
                query_hash TEXT NOT NULL,
                chunk_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS manifests (
                manifest_id TEXT PRIMARY KEY,
                manifest_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TEMP TABLE IF NOT EXISTS authorized_ids (
                chunk_id TEXT PRIMARY KEY
            );
            """
        )
        try:
            self.connection.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    content,
                    source_path,
                    symbol,
                    section_path,
                    tokenize='unicode61'
                )
                """
            )
            self.fts_available = True
        except sqlite3.OperationalError:
            self.fts_available = False
        self.connection.commit()

    @staticmethod
    def _json(value: Mapping[str, Any]) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def get_parse_cache(
        self, source_version: str, strategy: str, chunker_version: str
    ) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT content_hash, chunks_json FROM parse_cache
            WHERE source_version = ? AND strategy = ? AND chunker_version = ?
            """,
            (source_version, strategy, chunker_version),
        ).fetchone()
        if row is None:
            return None
        return {
            "content_hash": row["content_hash"],
            "chunks": json.loads(row["chunks_json"]),
        }

    def put_parse_cache(
        self,
        *,
        cache_key: str,
        source_version: str,
        strategy: str,
        chunker_version: str,
        content_hash: str,
        chunks: Sequence[Mapping[str, Any]],
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO parse_cache(
                cache_key, source_version, strategy, chunker_version, content_hash, chunks_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                content_hash=excluded.content_hash,
                chunks_json=excluded.chunks_json,
                created_at=CURRENT_TIMESTAMP
            """,
            (
                cache_key,
                source_version,
                strategy,
                chunker_version,
                content_hash,
                json.dumps(list(chunks), sort_keys=True, separators=(",", ":")),
            ),
        )
        self.connection.commit()

    def upsert_document(self, metadata: Mapping[str, Any]) -> None:
        self.connection.execute(
            """
            INSERT INTO documents(document_id, source_uri, source_kind, source_version, content_hash, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET
                source_uri=excluded.source_uri,
                source_kind=excluded.source_kind,
                source_version=excluded.source_version,
                content_hash=excluded.content_hash,
                metadata_json=excluded.metadata_json
            """,
            (
                metadata["document_id"],
                metadata["source_uri"],
                metadata["source_kind"],
                metadata["source_version"],
                metadata["content_hash"],
                self._json(metadata),
            ),
        )

    def replace_document_chunks(
        self, document_id: str, chunks: Sequence[tuple[Mapping[str, Any], str]]
    ) -> None:
        old_ids = [
            row[0]
            for row in self.connection.execute(
                "SELECT chunk_id FROM chunks WHERE document_id = ?", (document_id,)
            )
        ]
        if self.fts_available:
            for chunk_id in old_ids:
                self.connection.execute(
                    "DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,)
                )
        self.connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        for metadata, content in chunks:
            section_path = " / ".join(metadata.get("section_path", []))
            self.connection.execute(
                """
                INSERT INTO chunks(
                    chunk_id, document_id, content, metadata_json, source_kind,
                    evidence_class, sensitivity, solver_visible, task_id, task_commit,
                    control_plane_commit, source_path, symbol, section_path, ordinal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata["chunk_id"],
                    metadata["document_id"],
                    content,
                    self._json(metadata),
                    metadata["source_kind"],
                    metadata["evidence_class"],
                    metadata["sensitivity"],
                    1 if metadata["solver_visible"] else 0,
                    metadata.get("task_id"),
                    metadata.get("task_commit"),
                    metadata.get("control_plane_commit"),
                    metadata.get("source_path"),
                    metadata.get("symbol"),
                    section_path,
                    metadata["ordinal"],
                ),
            )
            if self.fts_available:
                self.connection.execute(
                    "INSERT INTO chunks_fts(chunk_id, content, source_path, symbol, section_path) VALUES (?, ?, ?, ?, ?)",
                    (
                        metadata["chunk_id"],
                        content,
                        metadata.get("source_path", ""),
                        metadata.get("symbol", ""),
                        section_path,
                    ),
                )
        self.connection.commit()

    def candidate_rows(
        self,
        *,
        source_kinds: Sequence[str] = (),
        evidence_classes: Sequence[str] = (),
        source_paths: Sequence[str] = (),
        symbols: Sequence[str] = (),
        section_terms: Sequence[str] = (),
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[Any] = []

        def add_in(field: str, items: Sequence[str]) -> None:
            if not items:
                return
            clauses.append(f"{field} IN ({','.join('?' for _ in items)})")
            values.extend(items)

        add_in("source_kind", source_kinds)
        add_in("evidence_class", evidence_classes)
        add_in("source_path", source_paths)
        add_in("symbol", symbols)
        for term in section_terms:
            clauses.append("section_path LIKE ?")
            values.append(f"%{term}%")
        sql = "SELECT chunk_id, document_id, content, metadata_json FROM chunks"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY source_path, ordinal, chunk_id"
        rows = []
        for row in self.connection.execute(sql, values):
            rows.append(
                {
                    "chunk_id": row["chunk_id"],
                    "document_id": row["document_id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata_json"]),
                }
            )
        return rows

    def rows_by_ids(self, chunk_ids: Iterable[str]) -> list[dict[str, Any]]:
        ids = tuple(dict.fromkeys(chunk_ids))
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self.connection.execute(
            f"SELECT chunk_id, document_id, content, metadata_json FROM chunks WHERE chunk_id IN ({placeholders})",
            ids,
        )
        by_id = {
            row["chunk_id"]: {
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "content": row["content"],
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in rows
        }
        return [by_id[chunk_id] for chunk_id in ids if chunk_id in by_id]

    def lexical_search(
        self, query: str, candidate_ids: Sequence[str], limit: int
    ) -> list[tuple[str, float]]:
        ids = tuple(dict.fromkeys(candidate_ids))
        tokens = [token.lower() for token in _TOKEN.findall(query)]
        if not ids or not tokens or limit <= 0:
            return []
        if self.fts_available:
            try:
                return self._fts_search(tokens, ids, limit)
            except sqlite3.OperationalError:
                pass
        return self._python_bm25(tokens, ids, limit)

    def _fts_search(
        self, tokens: Sequence[str], candidate_ids: Sequence[str], limit: int
    ) -> list[tuple[str, float]]:
        self.connection.execute("DELETE FROM authorized_ids")
        self.connection.executemany(
            "INSERT INTO authorized_ids(chunk_id) VALUES (?)",
            ((chunk_id,) for chunk_id in candidate_ids),
        )
        expression = " OR ".join(f'"{token.replace(chr(34), "")}"' for token in tokens)
        rows = self.connection.execute(
            """
            SELECT chunks_fts.chunk_id AS chunk_id, bm25(chunks_fts) AS raw_score
            FROM chunks_fts
            JOIN authorized_ids ON authorized_ids.chunk_id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH ?
            ORDER BY raw_score ASC
            LIMIT ?
            """,
            (expression, limit),
        )
        return [(row["chunk_id"], 1.0 / (1.0 + abs(row["raw_score"]))) for row in rows]

    def _python_bm25(
        self, tokens: Sequence[str], candidate_ids: Sequence[str], limit: int
    ) -> list[tuple[str, float]]:
        rows = self.rows_by_ids(candidate_ids)
        documents = [
            [token.lower() for token in _TOKEN.findall(row["content"])] for row in rows
        ]
        if not documents:
            return []
        average_length = sum(map(len, documents)) / max(1, len(documents))
        document_frequency = Counter()
        for document in documents:
            document_frequency.update(set(document))
        total = len(documents)
        k1 = 1.5
        b = 0.75
        scored: list[tuple[str, float]] = []
        for row, document in zip(rows, documents, strict=True):
            frequencies = Counter(document)
            score = 0.0
            for token in tokens:
                frequency = frequencies[token]
                if not frequency:
                    continue
                df = document_frequency[token]
                idf = math.log(1.0 + (total - df + 0.5) / (df + 0.5))
                denominator = frequency + k1 * (
                    1.0 - b + b * len(document) / max(1.0, average_length)
                )
                score += idf * (frequency * (k1 + 1.0)) / denominator
            if score > 0:
                scored.append((row["chunk_id"], score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:limit]

    def get_embedding(
        self, chunk_id: str, provider: str, provider_version: str, content_hash: str
    ) -> list[float] | None:
        row = self.connection.execute(
            """
            SELECT vector_json, content_hash FROM embeddings
            WHERE chunk_id = ? AND provider = ? AND provider_version = ?
            """,
            (chunk_id, provider, provider_version),
        ).fetchone()
        if row is None or row["content_hash"] != content_hash:
            return None
        return [float(value) for value in json.loads(row["vector_json"])]

    def put_embedding(
        self,
        chunk_id: str,
        provider: str,
        provider_version: str,
        content_hash: str,
        vector: Sequence[float],
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO embeddings(chunk_id, provider, provider_version, content_hash, vector_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id, provider, provider_version) DO UPDATE SET
                content_hash=excluded.content_hash,
                vector_json=excluded.vector_json
            """,
            (
                chunk_id,
                provider,
                provider_version,
                content_hash,
                json.dumps(list(vector), separators=(",", ":")),
            ),
        )
        self.connection.commit()

    def get_cached_result(self, cache_key: str) -> tuple[str, ...] | None:
        row = self.connection.execute(
            "SELECT chunk_ids_json FROM retrieval_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None:
            return None
        return tuple(json.loads(row["chunk_ids_json"]))

    def put_cached_result(
        self,
        cache_key: str,
        authority_hash: str,
        query_hash: str,
        chunk_ids: Sequence[str],
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO retrieval_cache(cache_key, authority_hash, query_hash, chunk_ids_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                authority_hash=excluded.authority_hash,
                query_hash=excluded.query_hash,
                chunk_ids_json=excluded.chunk_ids_json,
                created_at=CURRENT_TIMESTAMP
            """,
            (cache_key, authority_hash, query_hash, json.dumps(list(chunk_ids))),
        )
        self.connection.commit()

    def put_manifest(self, manifest_id: str, manifest: Mapping[str, Any]) -> None:
        self.connection.execute(
            """
            INSERT INTO manifests(manifest_id, manifest_json) VALUES (?, ?)
            ON CONFLICT(manifest_id) DO UPDATE SET
                manifest_json=excluded.manifest_json,
                created_at=CURRENT_TIMESTAMP
            """,
            (manifest_id, self._json(manifest)),
        )
        self.connection.commit()

    def latest_manifest(self) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT manifest_json FROM manifests ORDER BY created_at DESC, rowid DESC LIMIT 1"
        ).fetchone()
        return json.loads(row["manifest_json"]) if row is not None else None

    def stats(self) -> dict[str, Any]:
        documents = self.connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunks = self.connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        parse_cache = self.connection.execute("SELECT COUNT(*) FROM parse_cache").fetchone()[0]
        embeddings = self.connection.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        cached = self.connection.execute("SELECT COUNT(*) FROM retrieval_cache").fetchone()[0]
        return {
            "documents": documents,
            "chunks": chunks,
            "parse_cache_entries": parse_cache,
            "embeddings": embeddings,
            "retrieval_cache_entries": cached,
            "fts5": self.fts_available,
        }
