from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from retrieval.indexer import RepositoryIndexer  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402
from retrieval.store import RetrievalStore  # noqa: E402


def test_commit_bound_index_reuses_structural_parse_cache(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        indexer = RepositoryIndexer(ROOT, store, policy)
        first = indexer.build()
        first_stats = store.stats()
        second = indexer.build()
        second_stats = store.stats()

        assert first["source_set_hash"] == second["source_set_hash"]
        assert first["document_count"] == second["document_count"]
        assert first["chunk_count"] == second["chunk_count"]
        assert first_stats["parse_cache_entries"] > 0
        assert second_stats["parse_cache_entries"] == first_stats["parse_cache_entries"]
        assert second_stats["documents"] == first_stats["documents"]
        assert second_stats["chunks"] == first_stats["chunks"]
