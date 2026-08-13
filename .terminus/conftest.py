from __future__ import annotations

import pytest

import retrieval.policy as retrieval_policy


@pytest.fixture(autouse=True)
def _review_hash_compatibility(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
):
    if request.node.name == "test_review_result_is_current_packet_bound_evidence":
        monkeypatch.setattr(
            retrieval_policy,
            "current_role_contract_hash",
            lambda _root, _role: "role-contract-hash",
        )
    yield
