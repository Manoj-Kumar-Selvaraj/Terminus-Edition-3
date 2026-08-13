from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from retrieval.chunking import chunk_text  # noqa: E402
from retrieval.engine import RetrievalEngine  # noqa: E402
from retrieval.indexer import RepositoryIndexer  # noqa: E402
from retrieval.models import InvocationContext, RetrievalQuery  # noqa: E402
from retrieval.policy import ALL_ROLES, ALL_STAGES, RetrievalPolicy  # noqa: E402
from retrieval.store import RetrievalStore  # noqa: E402

TASK_ID = "retrieval-test-task"
TASK_COMMIT = "a" * 40
OTHER_TASK_COMMIT = "b" * 40
CONTROL_COMMIT = "c" * 40
ROLE_HASH = "role-contract-hash"
PACKET = "packet-current"


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _add_chunk(
    store: RetrievalStore,
    policy: RetrievalPolicy,
    *,
    source_kind: str,
    content: str,
    source_path: str,
    task_commit: str = TASK_COMMIT,
    packet_binding: str = PACKET,
    evidence_override: str | None = None,
    solver_visible_override: bool | None = None,
    stages: list[str] | None = None,
    roles: list[str] | None = None,
) -> dict[str, object]:
    profile = policy.source_profiles[source_kind]
    document_id = "doc_" + hashlib.sha256(source_path.encode()).hexdigest()
    chunk_id = "chk_" + hashlib.sha256((source_path + content).encode()).hexdigest()
    blob = "d" * 40
    metadata: dict[str, object] = {
        "metadata_contract_version": "1.0",
        "document_id": document_id,
        "chunk_id": chunk_id,
        "source_uri": f"git://test/{source_path}",
        "source_path": source_path,
        "source_kind": source_kind,
        "source_version": blob,
        "content_hash": _hash(content),
        "git_blob_sha": blob,
        "evidence_class": evidence_override or profile["default_evidence_class"],
        "sensitivity": profile["default_sensitivity"],
        "solver_visible": (
            profile["default_solver_visible"]
            if solver_visible_override is None
            else solver_visible_override
        ),
        "stage_applicability": stages or [ALL_STAGES],
        "role_applicability": roles or [ALL_ROLES],
        "freshness_scope": list(profile["required_freshness"]),
        "chunk_type": "DOCUMENT",
        "structural_locator": "document",
        "ordinal": 0,
        "control_plane_commit": CONTROL_COMMIT,
    }
    if profile.get("task_scoped"):
        metadata["task_id"] = TASK_ID
        metadata["task_commit"] = task_commit
    if "ROLE_CONTRACT_HASH" in profile["required_freshness"]:
        metadata["role_contract_hash"] = ROLE_HASH
    if "PACKET_BINDING" in profile["required_freshness"]:
        metadata["packet_binding"] = packet_binding
    if "POLICY_VERSION" in profile["required_freshness"]:
        metadata["policy_versions"] = {"agent_system": "2.4"}
    if "CI_RUN_ID" in profile["required_freshness"]:
        metadata["ci_run_id"] = "123"

    store.upsert_document(metadata)
    store.replace_document_chunks(document_id, [(metadata, content)])
    return metadata


def _context(
    stage: str,
    role: str,
    *,
    task_commit: str = TASK_COMMIT,
    packet_binding: str | None = None,
) -> InvocationContext:
    return InvocationContext(
        stage_id=stage,
        role_id=role,
        task_id=TASK_ID,
        task_commit=task_commit,
        control_plane_commit=CONTROL_COMMIT,
        role_contract_hash=ROLE_HASH,
        packet_binding=packet_binding,
        policy_versions={"agent_system": "2.4"},
    )


def test_instruction_draft_never_retrieves_oracle(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        _add_chunk(
            store,
            policy,
            source_kind="TASK_INSTRUCTION",
            content="Replay recovery must remain idempotent across restart.",
            source_path="task/instruction.md",
        )
        _add_chunk(
            store,
            policy,
            source_kind="SOLUTION_ORACLE",
            content="Secret oracle replay implementation and repair recipe.",
            source_path="task/solution/solve.py",
        )
        engine = RetrievalEngine(ROOT, store, policy=policy)
        results = engine.retrieve(
            _context("INSTRUCTION_DRAFT", "A7_INSTRUCTION_WRITER"),
            RetrievalQuery(text="replay recovery", mode="hybrid", limit=10),
        )
        assert results
        assert {result.metadata["source_kind"] for result in results} == {
            "TASK_INSTRUCTION"
        }


def test_solver_visible_only_rejects_shadow_requirement_contract(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        _add_chunk(
            store,
            policy,
            source_kind="TASK_INSTRUCTION",
            content="Public solver-visible model context.",
            source_path="task/instruction.md",
        )
        _add_chunk(
            store,
            policy,
            source_kind="SOLVER_VISIBLE_REQUIREMENT_CONTRACT",
            content="Controller-only sanitized shadow contract.",
            source_path=".terminus/contracts/retrieval-test-task/solver-visible-requirements.json",
            roles=[ALL_ROLES],
            stages=[ALL_STAGES],
        )
        engine = RetrievalEngine(ROOT, store, policy=policy)
        results = engine.retrieve(
            _context(
                "MODEL_DIAGNOSTIC",
                "Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR",
            ),
            RetrievalQuery(text="context contract", mode="hybrid", limit=10),
        )
        assert results
        assert all(result.metadata["solver_visible"] is True for result in results)
        assert all(
            result.metadata["source_kind"] != "SOLVER_VISIBLE_REQUIREMENT_CONTRACT"
            for result in results
        )


def test_stale_task_commit_is_filtered_before_ranking(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        _add_chunk(
            store,
            policy,
            source_kind="TASK_INSTRUCTION",
            content="Replay recovery material.",
            source_path="task/instruction.md",
            task_commit=TASK_COMMIT,
        )
        engine = RetrievalEngine(ROOT, store, policy=policy)
        results = engine.retrieve(
            _context(
                "INSTRUCTION_DRAFT",
                "A7_INSTRUCTION_WRITER",
                task_commit=OTHER_TASK_COMMIT,
            ),
            RetrievalQuery(text="replay", mode="hybrid"),
        )
        assert results == []


def test_packet_binding_cannot_cross_review_invocations(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        _add_chunk(
            store,
            policy,
            source_kind="REVIEW_PACKET",
            content="Current packet evidence for continuity review.",
            source_path=".terminus/reviews/task/current.packet.json",
            packet_binding=PACKET,
        )
        engine = RetrievalEngine(ROOT, store, policy=policy)
        blocked = engine.retrieve(
            _context(
                "QUALITY_INTERLOCK",
                "Q4_SPEC_TEST_CONTRACT_REVIEWER",
                packet_binding="different-packet",
            ),
            RetrievalQuery(text="packet evidence", mode="exact"),
        )
        allowed = engine.retrieve(
            _context(
                "QUALITY_INTERLOCK",
                "Q4_SPEC_TEST_CONTRACT_REVIEWER",
                packet_binding=PACKET,
            ),
            RetrievalQuery(text="packet evidence", mode="exact"),
        )
        assert blocked == []
        assert len(allowed) == 1


def test_source_profile_mismatch_fails_closed(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        _add_chunk(
            store,
            policy,
            source_kind="SOLUTION_ORACLE",
            content="Oracle pretending to be solver-visible.",
            source_path="task/solution/solve.py",
            evidence_override="SOLVER_VISIBLE_TASK",
        )
        engine = RetrievalEngine(ROOT, store, policy=policy)
        results = engine.retrieve(
            _context("INSTRUCTION_DRAFT", "A7_INSTRUCTION_WRITER"),
            RetrievalQuery(text="oracle", mode="hybrid"),
        )
        assert results == []


def test_unknown_role_fails_before_retrieval(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        engine = RetrievalEngine(ROOT, store, policy=policy)
        with pytest.raises(ValueError, match="unknown retrieval role"):
            engine.retrieve(
                _context("INSTRUCTION_DRAFT", "Q4_SPEC_REVIEWER"),
                RetrievalQuery(text="anything"),
            )


def test_exact_only_stage_cannot_be_upgraded_to_vector(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        _add_chunk(
            store,
            policy,
            source_kind="CONTROL_PLANE_MARKDOWN",
            content="Agent system policy conflict resolution.",
            source_path=".terminus/AGENT_SYSTEM.md",
        )
        engine = RetrievalEngine(ROOT, store, policy=policy)
        results = engine.retrieve(
            InvocationContext(
                stage_id="RULE_RESOLUTION",
                role_id="CREATION_CONTROLLER",
                control_plane_commit=CONTROL_COMMIT,
            ),
            RetrievalQuery(text="policy conflict", mode="vector"),
        )
        assert len(results) == 1
        assert results[0].exact_score > 0
        assert results[0].vector_score == 0


def test_hybrid_retrieval_populates_embedding_and_result_caches(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        _add_chunk(
            store,
            policy,
            source_kind="TASK_INSTRUCTION",
            content="Replay must reconcile durable acknowledgement after restart.",
            source_path="task/instruction.md",
        )
        engine = RetrievalEngine(ROOT, store, policy=policy)
        context = _context("INSTRUCTION_DRAFT", "A7_INSTRUCTION_WRITER")
        query = RetrievalQuery(text="durable replay acknowledgement", mode="hybrid")
        first = engine.retrieve(context, query)
        first_stats = store.stats()
        second = engine.retrieve(context, query)
        second_stats = store.stats()
        assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
        assert first_stats["embeddings"] >= 1
        assert first_stats["retrieval_cache_entries"] >= 1
        assert second_stats["embeddings"] == first_stats["embeddings"]


def test_structural_markdown_chunking_preserves_heading_ancestry() -> None:
    chunks = chunk_text(
        Path("policy.md"),
        "# Root\nintro\n## Child\nrule\n## Next\nother\n",
        "HEADING_SECTION",
    )
    paths = [chunk.section_path for chunk in chunks if chunk.section_path]
    assert ("Root",) in paths
    assert ("Root", "Child") in paths
    assert ("Root", "Next") in paths


def test_real_control_plane_index_is_commit_bound(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        manifest = RepositoryIndexer(ROOT, store, policy).build()
        stats = store.stats()
        assert manifest["index_scope"] == "CONTROL_PLANE"
        assert manifest["control_plane_commit"]
        assert manifest["source_set_hash"].startswith("sha256:")
        assert manifest["document_count"] > 0
        assert manifest["chunk_count"] > 0
        assert stats["documents"] == manifest["document_count"]
        assert stats["chunks"] == manifest["chunk_count"]
