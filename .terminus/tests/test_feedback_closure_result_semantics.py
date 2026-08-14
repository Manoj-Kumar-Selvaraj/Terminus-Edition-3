from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from feedback.ingestion import FeedbackIngestor  # noqa: E402
from feedback.provenance import ProvenanceValidator  # noqa: E402
from feedback.registry import LearningStore  # noqa: E402

_TASK_ID = "jetstream-regional-stream-continuity"
_Q4_REVISE_RESULT = (
    ".terminus/reviews/jetstream-regional-stream-continuity/440aa838/"
    "jetstream-regional-stream-continuity-440aa838-spec-test-contract-7c5bbb5a2b.json"
)
_Q6_PASS_RESULT = (
    ".terminus/reviews/jetstream-regional-stream-continuity/440aa838/"
    "jetstream-regional-stream-continuity-440aa838-production-logic-a277a01448.json"
)


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _binding(path: str, *, commit: str | None = None) -> dict[str, str]:
    commit = commit or _head()
    raw = (ROOT / path).read_bytes()
    return {
        "kind": "RESULT",
        "ref": f"git:{commit}:{path}",
        "content_hash": "sha256:" + hashlib.sha256(raw).hexdigest(),
    }


def test_noncanonical_pseudo_pass_result_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = ProvenanceValidator(ROOT)
    path = ".terminus/reviews/feedback-test/pseudo-pass.json"
    binding = {
        "kind": "RESULT",
        "ref": f"git:{_head()}:{path}",
        "content_hash": "sha256:" + "0" * 64,
    }
    monkeypatch.setattr(
        validator.evidence, "validate", lambda value, _index: dict(value)
    )
    monkeypatch.setattr(validator, "_require_reachable", lambda _commit: None)
    monkeypatch.setattr(
        validator,
        "_git_json",
        lambda _commit, _path, _label: {
            "schema_version": "1.0",
            "task_id": "feedback-test",
            "producer": "Q4_SPEC_TEST_CONTRACT_REVIEWER",
            "result": "PASS",
        },
    )
    with pytest.raises(ValueError, match="not canonical"):
        validator.validate_review_result(
            binding=binding,
            producer="Q4_SPEC_TEST_CONTRACT_REVIEWER",
            task_id="feedback-test",
            task_commit=_head(),
            require_passing=True,
        )


def test_historical_canonical_q4_revise_is_ingestible_feedback(
    tmp_path: Path,
) -> None:
    payload = json.loads((ROOT / _Q4_REVISE_RESULT).read_text(encoding="utf-8"))
    store = LearningStore(
        ROOT,
        state_root=tmp_path / "state",
        knowledge_root=tmp_path / "knowledge",
    )
    event = FeedbackIngestor(ROOT, store=store).capture(
        source_type="INDEPENDENT_REVIEW",
        producer="Q4_SPEC_TEST_CONTRACT_REVIEWER",
        task_id=_TASK_ID,
        task_commit=str(payload["task_commit"]),
        severity="HIGH",
        message="Historical Q4 REVISE remains a valid feedback signal, not closure authority.",
        category="HISTORICAL_REVIEW_SIGNAL",
        stage_hint="QUALITY_INTERLOCK",
        source_binding=_binding(_Q4_REVISE_RESULT),
        captured_at="2026-08-14T00:00:00Z",
    )
    assert event["provenance"]["trust_status"] == "REPOSITORY_RESOLVED"


def test_real_q4_revise_result_cannot_authorize_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = json.loads((ROOT / _Q4_REVISE_RESULT).read_text(encoding="utf-8"))
    validator = ProvenanceValidator(ROOT)
    monkeypatch.setattr(
        validator, "_validate_packet", lambda *_args, **_kwargs: None
    )
    with pytest.raises(ValueError, match="passing outcome"):
        validator.validate_review_result(
            binding=_binding(_Q4_REVISE_RESULT),
            producer="Q4_SPEC_TEST_CONTRACT_REVIEWER",
            task_id=_TASK_ID,
            task_commit=str(payload["task_commit"]),
            require_passing=True,
        )


def test_real_historical_q6_pass_cannot_verify_newer_task_commit() -> None:
    validator = ProvenanceValidator(ROOT)
    with pytest.raises(ValueError, match="exact verification task commit"):
        validator.validate_review_result(
            binding=_binding(_Q6_PASS_RESULT),
            producer="Q6_PRODUCTION_LOGIC_AUDITOR",
            task_id=_TASK_ID,
            task_commit=_head(),
            require_passing=True,
        )


def test_adjudicator_conflict_result_requires_exact_resolution_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = ProvenanceValidator(ROOT)
    path = ".terminus/reviews/feedback-test/adjudication.json"
    binding = {
        "kind": "RESULT",
        "ref": f"git:{_head()}:{path}",
        "content_hash": "sha256:" + "0" * 64,
    }
    payload = {
        "role": "Adjudicator",
        "task": "feedback-test",
        "task_commit": _head(),
        "verdict": "APPROVE",
        "confidence": "HIGH",
        "evidence_status": "SUFFICIENT",
        "role_output": {},
    }
    conflict_binding = {
        "finding_id": "finding_" + "0" * 64,
        "conflict_type": "FEEDBACK_CONFLICT",
        "signal_ids": ["feedback_" + "0" * 64],
        "signal_claims": [
            {
                "feedback_id": "feedback_" + "0" * 64,
                "category": "A",
                "claim_hash": "sha256:" + "0" * 64,
            }
        ],
        "conflicting_categories": ["A", "B"],
    }
    monkeypatch.setattr(
        validator.evidence, "validate", lambda value, _index: dict(value)
    )
    monkeypatch.setattr(validator, "_require_reachable", lambda _commit: None)
    monkeypatch.setattr(validator, "_git_json", lambda *_args: payload)
    monkeypatch.setattr(
        "feedback.provenance.validate_schema", lambda *_args: None
    )
    monkeypatch.setattr(
        validator.semantic_authority,
        "verify",
        lambda *_args, **_kwargs: {},
    )
    with pytest.raises(ValueError, match="CONFLICT_RESOLUTION"):
        validator.validate_review_result(
            binding=binding,
            producer="ADJUDICATOR",
            task_id="feedback-test",
            task_commit=_head(),
            require_passing=True,
            conflict_resolution=True,
            conflict_binding=conflict_binding,
            require_current_contract=False,
        )


def test_unreachable_side_commit_cannot_be_review_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = ProvenanceValidator(ROOT)
    path = ".terminus/reviews/feedback-test/fake-result.json"
    binding = {
        "kind": "RESULT",
        "ref": f"git:{'0' * 40}:{path}",
        "content_hash": "sha256:" + "0" * 64,
    }
    monkeypatch.setattr(
        validator.evidence, "validate", lambda value, _index: dict(value)
    )
    with pytest.raises(ValueError, match="authorized repository lineage"):
        validator.validate_review_result(
            binding=binding,
            producer="Q4_SPEC_TEST_CONTRACT_REVIEWER",
            task_id="feedback-test",
            task_commit=_head(),
            require_passing=True,
        )
