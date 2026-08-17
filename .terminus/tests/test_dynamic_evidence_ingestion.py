from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from retrieval.engine import RetrievalEngine  # noqa: E402
from retrieval.ingestion import DynamicEvidenceIngestor  # noqa: E402
from retrieval.models import InvocationContext, RetrievalQuery  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402
from retrieval.store import RetrievalStore  # noqa: E402

TASK_ID = "jetstream-regional-stream-continuity"
TASK_COMMIT = "065cf6f02c08abf86074d3886069b22ef47831f6"
PACKET_PATH = (
    ".terminus/reviews/jetstream-regional-stream-continuity/065cf6f0/"
    "jetstream-regional-stream-continuity-065cf6f0-spec-test-contract-8244aef647.packet.json"
)
RESULT_PATH = (
    ".terminus/reviews/jetstream-regional-stream-continuity/f73b6c9a/"
    "jetstream-regional-stream-continuity-f73b6c9a-adjudication-e8e3160e31.json"
)
SESSION_PATH = ".terminus/sessions/jetstream-regional-stream-continuity.md"


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _last_commit(path: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "log", "-1", "--format=%H", "--", path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _row(store: RetrievalStore, document_id: str) -> dict[str, object]:
    rows = [
        row
        for row in store.candidate_rows()
        if row["document_id"] == document_id
    ]
    assert rows
    return rows[0]


def _context_from_row(row: dict[str, object], role_id: str) -> InvocationContext:
    metadata = row["metadata"]
    assert isinstance(metadata, dict)
    return InvocationContext(
        stage_id=str(metadata["stage_applicability"][0]),
        role_id=role_id,
        task_id=metadata.get("task_id"),
        task_commit=metadata.get("task_commit"),
        control_plane_commit=metadata.get("control_plane_commit"),
        role_contract_hash=metadata.get("role_contract_hash"),
        packet_binding=metadata.get("packet_binding"),
        review_scope_hash=metadata.get("review_scope_hash"),
        ci_run_id=metadata.get("ci_run_id"),
        policy_versions=metadata.get("policy_versions", {}),
    )


def test_review_packet_derives_bindings_and_stays_role_scoped(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        result = DynamicEvidenceIngestor(ROOT, store, policy).ingest_review_packet(
            source_path=PACKET_PATH,
            source_commit=_head(),
            stage_id="QUALITY_INTERLOCK",
            role_ids=["Q4_SPEC_TEST_CONTRACT_REVIEWER"],
        )
        row = _row(store, result["document_id"])
        metadata = row["metadata"]
        assert metadata["task_id"] == TASK_ID
        assert metadata["task_commit"] == TASK_COMMIT
        assert metadata["packet_binding"] == (
            "jetstream-regional-stream-continuity-065cf6f0-spec-test-contract-8244aef647"
        )
        assert metadata["role_applicability"] == ["Q4_SPEC_TEST_CONTRACT_REVIEWER"]

        engine = RetrievalEngine(ROOT, store, policy=policy)
        q4 = engine.retrieve(
            _context_from_row(row, "Q4_SPEC_TEST_CONTRACT_REVIEWER"),
            RetrievalQuery(text="FROZEN_CANDIDATE", mode="exact"),
        )
        q6 = engine.retrieve(
            _context_from_row(row, "Q6_PRODUCTION_LOGIC_AUDITOR"),
            RetrievalQuery(text="FROZEN_CANDIDATE", mode="exact"),
        )
        assert q4
        assert q6 == []


def test_packet_projection_rejects_other_stage_reviewer(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        with pytest.raises(ValueError, match="review packet may be projected only"):
            DynamicEvidenceIngestor(ROOT, store, policy).ingest_review_packet(
                source_path=PACKET_PATH,
                source_commit=_head(),
                stage_id="QUALITY_INTERLOCK",
                role_ids=["Q6_PRODUCTION_LOGIC_AUDITOR"],
            )


def test_review_result_preserves_producer_binding_for_controller_consumption(
    tmp_path: Path,
) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        result = DynamicEvidenceIngestor(ROOT, store, policy).ingest_review_result(
            source_path=RESULT_PATH,
            source_commit=_head(),
            stage_id="SUBMISSION_READY",
            role_ids=["CI_ORCHESTRATOR"],
        )
        row = _row(store, result["document_id"])
        metadata = row["metadata"]
        assert metadata["role_applicability"] == ["CI_ORCHESTRATOR"]
        assert metadata["role_contract_hash"]
        assert metadata["packet_binding"].endswith("adjudication-e8e3160e31")

        results = RetrievalEngine(ROOT, store, policy=policy).retrieve(
            _context_from_row(row, "CI_ORCHESTRATOR"),
            RetrievalQuery(text="REQUEST_CHANGES", mode="exact"),
        )
        assert results


def test_session_ingestion_derives_policy_versions_and_fails_stale_context(
    tmp_path: Path,
) -> None:
    policy = RetrievalPolicy(ROOT)
    source_commit = _last_commit(SESSION_PATH)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        result = DynamicEvidenceIngestor(ROOT, store, policy).ingest_session_state(
            source_path=SESSION_PATH,
            source_commit=source_commit,
            stage_id="RULE_RESOLUTION",
            role_ids=["CREATION_CONTROLLER"],
        )
        row = _row(store, result["document_id"])
        metadata = row["metadata"]
        assert metadata["policy_versions"]["agent_system"]
        assert metadata["policy_versions"]["specialist_protocol"]
        assert metadata["control_plane_commit"] == source_commit

        engine = RetrievalEngine(ROOT, store, policy=policy)
        current = engine.retrieve(
            _context_from_row(row, "CREATION_CONTROLLER"),
            RetrievalQuery(text="FROZEN_CANDIDATE", mode="exact"),
        )
        stale_context = _context_from_row(row, "CREATION_CONTROLLER")
        stale_context = InvocationContext(
            stage_id=stale_context.stage_id,
            role_id=stale_context.role_id,
            task_id=stale_context.task_id,
            task_commit=stale_context.task_commit,
            control_plane_commit=stale_context.control_plane_commit,
            policy_versions={**stale_context.policy_versions, "agent_system": "9.9"},
        )
        stale = engine.retrieve(
            stale_context,
            RetrievalQuery(text="FROZEN_CANDIDATE", mode="exact"),
        )
        assert current
        assert stale == []


def test_ci_runtime_requires_run_binding_and_rejects_wrong_run(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        ingestor = DynamicEvidenceIngestor(ROOT, store, policy)
        with pytest.raises(ValueError, match="missing required provenance bindings"):
            ingestor.ingest_external(
                source_kind="CI_RUNTIME",
                content="Oracle 40/40 PASS",
                source_uri="github-actions://run/31388325311/job/93453835600",
                stage_id="DETERMINISTIC_VALIDATION",
                role_ids=["CI_ORCHESTRATOR"],
                task_id=TASK_ID,
                task_commit=TASK_COMMIT,
            )

        result = ingestor.ingest_external(
            source_kind="CI_RUNTIME",
            content="Oracle 40/40 PASS; NOP reward 0",
            source_uri="github-actions://run/31388325311/job/93453835600",
            stage_id="DETERMINISTIC_VALIDATION",
            role_ids=["CI_ORCHESTRATOR"],
            task_id=TASK_ID,
            task_commit=TASK_COMMIT,
            ci_run_id="31388325311",
        )
        row = _row(store, result["document_id"])
        engine = RetrievalEngine(ROOT, store, policy=policy)
        current = engine.retrieve(
            _context_from_row(row, "CI_ORCHESTRATOR"),
            RetrievalQuery(text="Oracle 40/40", mode="exact"),
        )
        wrong = _context_from_row(row, "CI_ORCHESTRATOR")
        wrong = InvocationContext(
            stage_id=wrong.stage_id,
            role_id=wrong.role_id,
            task_id=wrong.task_id,
            task_commit=wrong.task_commit,
            ci_run_id="different-run",
        )
        stale = engine.retrieve(
            wrong,
            RetrievalQuery(text="Oracle 40/40", mode="exact"),
        )
        assert current
        assert stale == []


def test_external_evidence_is_content_addressed_and_stage_filtered(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    with RetrievalStore(tmp_path / "retrieval.sqlite3") as store:
        ingestor = DynamicEvidenceIngestor(ROOT, store, policy)
        first = ingestor.ingest_external(
            source_kind="MODEL_TRIAL",
            content="trial one: solver timed out at replay reconciliation",
            source_uri="model-trial://gpt-5.5/run-1",
            stage_id="TRIAL_ANALYSIS",
            role_ids=["TRAJECTORY_ANALYST"],
            task_id=TASK_ID,
            task_commit=TASK_COMMIT,
        )
        second = ingestor.ingest_external(
            source_kind="MODEL_TRIAL",
            content="trial one: solver completed replay reconciliation",
            source_uri="model-trial://gpt-5.5/run-1",
            stage_id="TRIAL_ANALYSIS",
            role_ids=["TRAJECTORY_ANALYST"],
            task_id=TASK_ID,
            task_commit=TASK_COMMIT,
        )
        assert first["source_version"].startswith("sha256:")
        assert first["source_version"] != second["source_version"]
        assert first["document_id"] != second["document_id"]

        with pytest.raises(ValueError, match="dynamic evidence projection denied"):
            ingestor.ingest_external(
                source_kind="MODEL_TRIAL",
                content="trial evidence",
                source_uri="model-trial://gpt-5.5/run-2",
                stage_id="QUALITY_INTERLOCK",
                role_ids=["CI_ORCHESTRATOR"],
                task_id=TASK_ID,
                task_commit=TASK_COMMIT,
            )
