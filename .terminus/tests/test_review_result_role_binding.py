from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from review_contract import role_contract_hash  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402

TASK = "review-role-binding-test"
TASK_COMMIT = "a" * 40
CONTROL_COMMIT = "b" * 40
PACKET = "q4-review"


def _metadata(policy: RetrievalPolicy) -> dict[str, object]:
    profile = policy.source_profiles["REVIEW_RESULT"]
    return {
        "source_kind": "REVIEW_RESULT",
        "evidence_class": profile["default_evidence_class"],
        "sensitivity": profile["default_sensitivity"],
        "solver_visible": profile["default_solver_visible"],
        "stage_applicability": ["QUALITY_INTERLOCK"],
        "role_applicability": [
            "Q4_SPEC_TEST_CONTRACT_REVIEWER",
            "Q6_PRODUCTION_LOGIC_AUDITOR",
            "CI_ORCHESTRATOR",
        ],
        "freshness_scope": list(profile["required_freshness"]),
        "task_id": TASK,
        "task_commit": TASK_COMMIT,
        "control_plane_commit": CONTROL_COMMIT,
        "role_contract_hash": role_contract_hash(ROOT, "Spec-Test Contract Reviewer"),
        "packet_binding": PACKET,
    }


def _context(role: str, role_hash: str) -> InvocationContext:
    return InvocationContext(
        stage_id="QUALITY_INTERLOCK",
        role_id=role,
        task_id=TASK,
        task_commit=TASK_COMMIT,
        control_plane_commit=CONTROL_COMMIT,
        role_contract_hash=role_hash,
        packet_binding=PACKET,
    )


def test_result_matches_producer_role() -> None:
    policy = RetrievalPolicy(ROOT)
    metadata = _metadata(policy)
    q4_hash = role_contract_hash(ROOT, "Spec-Test Contract Reviewer")
    decision = policy.authorize_chunk(
        metadata,
        _context("Q4_SPEC_TEST_CONTRACT_REVIEWER", q4_hash),
    )
    assert decision.allowed


def test_result_does_not_match_sibling_role() -> None:
    policy = RetrievalPolicy(ROOT)
    metadata = _metadata(policy)
    q6_hash = role_contract_hash(ROOT, "Production Logic Auditor")
    decision = policy.authorize_chunk(
        metadata,
        _context("Q6_PRODUCTION_LOGIC_AUDITOR", q6_hash),
    )
    assert decision.allowed is False
    assert decision.reason == "cold-review result producer mismatch"


def test_sibling_role_requires_its_own_contract_hash() -> None:
    policy = RetrievalPolicy(ROOT)
    metadata = _metadata(policy)
    q4_hash = role_contract_hash(ROOT, "Spec-Test Contract Reviewer")
    decision = policy.authorize_chunk(
        metadata,
        _context("Q6_PRODUCTION_LOGIC_AUDITOR", q4_hash),
    )
    assert decision.allowed is False
    assert decision.reason == "review result consumer role-contract hash mismatch"


def test_controller_can_read_producer_bound_result() -> None:
    policy = RetrievalPolicy(ROOT)
    metadata = _metadata(policy)
    q4_hash = role_contract_hash(ROOT, "Spec-Test Contract Reviewer")
    decision = policy.authorize_chunk(
        metadata,
        _context("CI_ORCHESTRATOR", q4_hash),
    )
    assert decision.allowed
