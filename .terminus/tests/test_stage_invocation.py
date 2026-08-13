from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.invocation import StageInvocationBuilder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import ALL_ROLES, ALL_STAGES, RetrievalPolicy  # noqa: E402
from retrieval.store import RetrievalStore  # noqa: E402

CONTROL_COMMIT = "c" * 40
TASK_COMMIT = "a" * 40


def _context(stage: str, role: str = "CI_ORCHESTRATOR") -> InvocationContext:
    return InvocationContext(
        stage_id=stage,
        role_id=role,
        control_plane_commit=CONTROL_COMMIT,
        policy_versions={"agent_system": "2.4"},
    )


def _required_inputs(policy: RetrievalPolicy, stage_id: str) -> dict[str, object]:
    fields = policy.stages[stage_id]["input_contract"]["required_fields"]
    return {str(field): {"ref": f"test:{field}"} for field in fields}


def _walk_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key).lower())
            keys.update(_walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_walk_keys(item))
    return keys


def _add_control_plane_chunk(store: RetrievalStore, policy: RetrievalPolicy) -> None:
    content = "policy authority routing"
    digest = hashlib.sha256(content.encode()).hexdigest()
    document_id = "doc_" + hashlib.sha256(b"policy-doc").hexdigest()
    chunk_id = "chk_" + hashlib.sha256(b"policy-chunk").hexdigest()
    profile = policy.source_profiles["CONTROL_PLANE_MARKDOWN"]
    metadata = {
        "metadata_contract_version": "1.0",
        "document_id": document_id,
        "chunk_id": chunk_id,
        "source_uri": "git://test/.terminus/policy.md",
        "source_path": ".terminus/policy.md",
        "source_kind": "CONTROL_PLANE_MARKDOWN",
        "source_version": "d" * 40,
        "content_hash": f"sha256:{digest}",
        "git_blob_sha": "d" * 40,
        "evidence_class": profile["default_evidence_class"],
        "sensitivity": profile["default_sensitivity"],
        "solver_visible": profile["default_solver_visible"],
        "stage_applicability": [ALL_STAGES],
        "role_applicability": [ALL_ROLES],
        "freshness_scope": list(profile["required_freshness"]),
        "chunk_type": "HEADING_SECTION",
        "structural_locator": "policy",
        "ordinal": 0,
        "control_plane_commit": CONTROL_COMMIT,
    }
    store.upsert_document(metadata)
    store.replace_document_chunks(document_id, [(metadata, content)])


def test_all_registered_stages_compile_from_machine_contract() -> None:
    policy = RetrievalPolicy(ROOT)
    builder = StageInvocationBuilder(ROOT, policy)
    assert len(policy.stages) == 23
    for stage_id, stage in policy.stages.items():
        packet = builder.build(_context(stage_id), _required_inputs(policy, stage_id))
        assert packet["readiness"] == "READY", stage_id
        assert packet["stage"]["stage_id"] == stage_id
        assert packet["stage"]["role_id"] == "CI_ORCHESTRATOR"
        assert packet["output_contract"]["allowed_status_values"] == stage["output_contract"]["status_values"]
        assert packet["routing"]["success_transition"] == stage["success_transition"]
        assert packet["evidence"]["mandatory_exact_reads"] == list(
            policy.mandatory_exact_paths(stage_id)
        )


def test_missing_required_inputs_produces_blocked_nonexecuting_packet() -> None:
    builder = StageInvocationBuilder(ROOT)
    packet = builder.build(
        _context("RULE_RESOLUTION"),
        {},
        retrieval_query="authority",
    )
    assert packet["readiness"] == "BLOCKED_MISSING_INPUTS"
    assert packet["missing_required_inputs"] == ["CREATION_REQUEST"]
    assert packet["retrieval"]["status"] == "SKIPPED_BLOCKED_INPUTS"
    assert packet["retrieval"]["retrieved_context"] == []


def test_undeclared_inputs_are_not_projected() -> None:
    builder = StageInvocationBuilder(ROOT)
    packet = builder.build(
        _context("RULE_RESOLUTION"),
        {"CREATION_REQUEST": "create", "ORACLE_SECRET": "must-not-project"},
    )
    assert packet["readiness"] == "READY"
    assert "ORACLE_SECRET" not in packet["inputs"]["required"]
    assert "ORACLE_SECRET" not in packet["inputs"]["optional"]
    assert packet["ignored_input_fields"] == ["ORACLE_SECRET"]


def test_valid_role_cannot_build_handoff_for_wrong_stage() -> None:
    builder = StageInvocationBuilder(ROOT)
    with pytest.raises(ValueError, match="not authorized for stage"):
        builder.build(
            _context("DETERMINISTIC_VALIDATION", "Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR"),
            {},
        )


def test_task_identity_requires_exact_pair() -> None:
    builder = StageInvocationBuilder(ROOT)
    with pytest.raises(ValueError, match="supplied together"):
        builder.build(
            InvocationContext(
                stage_id="RULE_RESOLUTION",
                role_id="CI_ORCHESTRATOR",
                task_id="task-x",
                control_plane_commit=CONTROL_COMMIT,
            ),
            {"CREATION_REQUEST": "create"},
        )


def test_invocation_identity_is_stable_and_input_bound() -> None:
    builder = StageInvocationBuilder(ROOT)
    first = builder.build(
        _context("RULE_RESOLUTION"), {"CREATION_REQUEST": {"goal": "one"}}
    )
    second = builder.build(
        _context("RULE_RESOLUTION"), {"CREATION_REQUEST": {"goal": "one"}}
    )
    changed = builder.build(
        _context("RULE_RESOLUTION"), {"CREATION_REQUEST": {"goal": "two"}}
    )
    assert first["invocation_id"] == second["invocation_id"]
    assert first["invocation_id"] != changed["invocation_id"]


def test_packet_has_no_private_reasoning_fields() -> None:
    builder = StageInvocationBuilder(ROOT)
    packet = builder.build(
        _context("RULE_RESOLUTION"), {"CREATION_REQUEST": "create"}
    )
    forbidden = {"chain_of_thought", "reasoning", "scratchpad", "private_reasoning"}
    assert not (_walk_keys(packet) & forbidden)


def test_indexed_context_is_authorized_and_bounded(tmp_path: Path) -> None:
    policy = RetrievalPolicy(ROOT)
    db = tmp_path / "retrieval.sqlite3"
    with RetrievalStore(db) as store:
        _add_control_plane_chunk(store, policy)
    packet = StageInvocationBuilder(ROOT, policy).build(
        _context("RULE_RESOLUTION"),
        {"CREATION_REQUEST": "create"},
        retrieval_query="policy authority",
        retrieval_db=db,
        max_chars=12,
    )
    assert packet["retrieval"]["status"] == "INDEXED_CONTEXT"
    assert packet["retrieval"]["retrieved_chars"] <= 12
    assert packet["retrieval"]["retrieved_context"]
    assert packet["retrieval"]["retrieved_context"][0]["evidence_class"] == "CONTROL_PLANE_POLICY"


def test_missing_index_preserves_normal_chatgpt_fallback(tmp_path: Path) -> None:
    packet = StageInvocationBuilder(ROOT).build(
        _context("RULE_RESOLUTION"),
        {"CREATION_REQUEST": "create"},
        retrieval_query="policy",
        retrieval_db=tmp_path / "absent.sqlite3",
    )
    assert packet["readiness"] == "READY"
    assert packet["retrieval"]["status"] == "DIRECT_READ_FALLBACK"
    assert packet["evidence"]["mandatory_exact_reads"]


def test_unknown_evidence_restriction_fails_closed() -> None:
    builder = StageInvocationBuilder(ROOT)
    with pytest.raises(ValueError, match="unknown excluded evidence classes"):
        builder.build(
            InvocationContext(
                stage_id="RULE_RESOLUTION",
                role_id="CI_ORCHESTRATOR",
                control_plane_commit=CONTROL_COMMIT,
                excluded_evidence_classes=frozenset({"NOT_A_REAL_CLASS"}),
            ),
            {"CREATION_REQUEST": "create"},
        )
