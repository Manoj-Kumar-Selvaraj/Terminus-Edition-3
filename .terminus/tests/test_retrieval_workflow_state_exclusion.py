from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from retrieval.indexer import RepositoryIndexer  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402
from retrieval.store import RetrievalStore  # noqa: E402


def test_execution_records_and_workflow_snapshots_are_not_static_rag_sources(
    tmp_path: Path,
) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        indexer = RepositoryIndexer(ROOT, store, policy)
        for path in (
            ".terminus/executions/task-a/inv_" + "a" * 64 + ".result.json",
            ".terminus/executions/task-a/ledger.jsonl",
            ".terminus/workflows/task-a/state.json",
        ):
            assert (
                indexer.classify_path(
                    path,
                    task_path=None,
                    include_private_design=False,
                )
                is None
            )


def test_execution_state_remains_excluded_even_when_task_indexing_is_enabled(
    tmp_path: Path,
) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        indexer = RepositoryIndexer(ROOT, store, policy)
        for path in (
            ".terminus/executions/task-a/ledger.jsonl",
            ".terminus/workflows/task-a/state.json",
        ):
            assert (
                indexer.classify_path(
                    path,
                    task_path="tasks/task-a",
                    include_private_design=True,
                )
                is None
            )
