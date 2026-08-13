from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from retrieval.engine import RetrievalEngine  # noqa: E402
from retrieval.indexer import RepositoryIndexer  # noqa: E402
from retrieval.models import InvocationContext, RetrievalQuery  # noqa: E402
from retrieval.policy import ALL_ROLES, ALL_STAGES, RetrievalPolicy  # noqa: E402
from retrieval.store import RetrievalStore  # noqa: E402

TASK_ID = "retrieval-test-task"
TASK_COMMIT = "a" * 40
CONTROL_COMMIT = "c" * 40
ROLE_HASH = "role-contract-hash"


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _context(stage: str, role: str) -> InvocationContext:
    return InvocationContext(
        stage_id=stage,
        role_id=role,
        task_id=TASK_ID,
        task_commit=TASK_COMMIT,
        control_plane_commit=CONTROL_COMMIT,
        role_contract_hash=ROLE_HASH,
        policy_versions={"agent_system": "2.4"},
    )


def _add_instruction(
    store: RetrievalStore,
    policy: RetrievalPolicy,
    *,
    source_path: str,
    content: str,
) -> str:
    profile = policy.source_profiles["TASK_INSTRUCTION"]
    document_id = "doc_" + hashlib.sha256(source_path.encode()).hexdigest()
    chunk_id = "chk_" + hashlib.sha256((source_path + content).encode()).hexdigest()
    blob = "d" * 40
    metadata = {
        "metadata_contract_version": "1.0",
        "document_id": document_id,
        "chunk_id": chunk_id,
        "source_uri": f"git://test/{source_path}",
        "source_path": source_path,
        "source_kind": "TASK_INSTRUCTION",
        "source_version": blob,
        "content_hash": _hash(content),
        "git_blob_sha": blob,
        "evidence_class": profile["default_evidence_class"],
        "sensitivity": profile["default_sensitivity"],
        "solver_visible": profile["default_solver_visible"],
        "stage_applicability": [ALL_STAGES],
        "role_applicability": [ALL_ROLES],
        "freshness_scope": list(profile["required_freshness"]),
        "chunk_type": "DOCUMENT",
        "structural_locator": "document",
        "ordinal": 0,
        "task_id": TASK_ID,
        "task_commit": TASK_COMMIT,
        "control_plane_commit": CONTROL_COMMIT,
    }
    store.upsert_document(metadata)
    store.replace_document_chunks(document_id, [(metadata, content)])
    return chunk_id


def test_valid_role_cannot_borrow_another_stage_authority(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        engine = RetrievalEngine(ROOT, store, policy=policy)
        with pytest.raises(ValueError, match="not authorized for stage"):
            engine.retrieve(
                _context(
                    "DETERMINISTIC_VALIDATION",
                    "Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR",
                ),
                RetrievalQuery(text="oracle"),
            )


def test_context_bundle_is_strictly_bounded(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        content = "replay " + ("x" * 500)
        _add_instruction(
            store,
            policy,
            source_path="task/instruction.md",
            content=content,
        )
        engine = RetrievalEngine(ROOT, store, policy=policy)
        bundle = engine.context_bundle(
            _context("INSTRUCTION_DRAFT", "A7_INSTRUCTION_WRITER"),
            RetrievalQuery(text="replay", mode="exact"),
            max_chars=64,
        )
        assert bundle["retrieved_chars"] == 64
        assert len(bundle["retrieved_context"][0]["content"]) == 64
        assert bundle["retrieved_context"][0]["truncated"] is True
        assert bundle["retrieved_context"][0]["content_hash"] == _hash(content)


def test_candidate_pool_change_invalidates_cached_ranking(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        first_id = _add_instruction(
            store,
            policy,
            source_path="task/z-old.md",
            content="replay only",
        )
        engine = RetrievalEngine(ROOT, store, policy=policy)
        context = _context("INSTRUCTION_DRAFT", "A7_INSTRUCTION_WRITER")
        query = RetrievalQuery(text="replay recovery durable", mode="exact", limit=10)
        first = engine.retrieve(context, query)
        assert [item.chunk_id for item in first] == [first_id]

        better_id = _add_instruction(
            store,
            policy,
            source_path="task/a-new.md",
            content="replay recovery durable",
        )
        second = engine.retrieve(context, query)
        assert second[0].chunk_id == better_id
        assert {item.chunk_id for item in second} == {first_id, better_id}


def test_parse_cache_identity_includes_parser_discriminator(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        indexer = RepositoryIndexer(ROOT, store, policy)
        python_key = indexer._parse_cache_strategy("module.py", "CODE_SYMBOL")
        shell_key = indexer._parse_cache_strategy("module.sh", "CODE_SYMBOL")
        assert python_key != shell_key


def test_index_build_preserves_independent_task_and_control_commits(
    tmp_path: Path,
) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        indexer = RepositoryIndexer(ROOT, store, policy)
        control_commit = "1" * 40
        task_commit = "2" * 40
        seen: list[tuple[str, str, str, str, str | None]] = []

        indexer._git = lambda *args: "unused-head\n"  # type: ignore[method-assign]
        indexer._tracked_paths = (  # type: ignore[method-assign]
            lambda commit: [".terminus/AGENT_SYSTEM.md"]
            if commit == control_commit
            else ["fake-task/instruction.md"]
        )

        def fake_index(
            relative: str,
            source_kind: str,
            *,
            source_commit: str,
            control_plane_commit: str,
            task_id: str | None,
            task_commit: str | None,
        ):
            seen.append(
                (
                    relative,
                    source_kind,
                    source_commit,
                    control_plane_commit,
                    task_commit,
                )
            )
            token = hashlib.sha256(relative.encode()).hexdigest()
            return f"doc-{token}", token, []

        indexer.index_git_file = fake_index  # type: ignore[method-assign]
        manifest = indexer.build(
            task_path="fake-task",
            task_id="fake-task",
            control_plane_commit=control_commit,
            task_commit=task_commit,
        )

        assert manifest["control_plane_commit"] == control_commit
        assert manifest["task_commit"] == task_commit
        assert (
            ".terminus/AGENT_SYSTEM.md",
            "CONTROL_PLANE_MARKDOWN",
            control_commit,
            control_commit,
            task_commit,
        ) in seen
        assert (
            "fake-task/instruction.md",
            "TASK_INSTRUCTION",
            task_commit,
            control_commit,
            task_commit,
        ) in seen
