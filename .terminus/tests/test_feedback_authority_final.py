from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))
sys.path.insert(0, str(ROOT / ".terminus" / "tests"))

from authority.receipts import AuthorityReceiptValidator  # noqa: E402
from authority_helpers import sign_receipt  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402
from feedback.ingestion import FeedbackIngestor  # noqa: E402
from feedback.model import lesson_identity, pattern_identity  # noqa: E402
from feedback.normalizer import FindingNormalizer  # noqa: E402
from feedback.registry import LearningStore  # noqa: E402
from learning.integrity import LearningIntegrityValidator  # noqa: E402


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _store(tmp_path: Path) -> LearningStore:
    return LearningStore(
        ROOT,
        state_root=tmp_path / "state",
        knowledge_root=tmp_path / "knowledge",
    )


def _policy_proof() -> dict[str, object]:
    source = ".terminus/agents/PROTOCOL.md"
    text = (ROOT / source).read_text(encoding="utf-8")
    decision_key = "RULE_RESOLUTION_ACTION"
    excerpts = [
        (
            "packet-authenticity",
            "Hand-written packets are not acceptance evidence.",
            "BLOCK_HAND_WRITTEN_PACKET",
        ),
        (
            "stale-review",
            "`STALE` is never PASS.",
            "BLOCK_STALE_REVIEW",
        ),
    ]
    rules: list[dict[str, object]] = []
    for rule_id, rule_text, required_value in excerpts:
        assert rule_text in text
        rules.append(
            {
                "source": source,
                "source_commit": _head(),
                "rule_id": rule_id,
                "rule_text": rule_text,
                "rule_hash": "sha256:"
                + hashlib.sha256(rule_text.encode("utf-8")).hexdigest(),
                "decision_key": decision_key,
                "required_value": required_value,
            }
        )
    return {
        "affected_gate": "RULE_RESOLUTION",
        "decision_key": decision_key,
        "conflict_statement": "Only an authenticated Adjudicator may assert that exact rules impose mutually exclusive values on one normalized decision.",
        "rules": rules,
    }


def _stub_learning_closure(monkeypatch: pytest.MonkeyPatch, validator: LearningIntegrityValidator) -> None:
    class StubClosure:
        @staticmethod
        def assert_learning_eligible(_finding) -> None:
            return None

    monkeypatch.setattr(validator, "_closure", lambda: StubClosure())


def test_authority_receipt_cannot_be_reused_for_different_claim() -> None:
    receipt = sign_receipt(
        "HUMAN_FEEDBACK",
        "human:alice",
        {"task_id": "task-a", "decision": "APPROVE"},
    )
    with pytest.raises(ValueError, match="exact semantic action"):
        AuthorityReceiptValidator(ROOT).verify(
            receipt,
            action="HUMAN_FEEDBACK",
            principal="human:alice",
            claim={"task_id": "task-a", "decision": "REJECT"},
        )


def test_repository_cannot_supply_authority_trust_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claim = {"task_id": "task-a"}
    receipt = sign_receipt("HUMAN_FEEDBACK", "human:alice", claim)
    monkeypatch.setenv(
        "TERMINUS_AUTHORITY_ALLOWED_SIGNERS",
        str(ROOT / ".terminus" / "AGENT_SYSTEM.md"),
    )
    with pytest.raises(ValueError, match="outside the repository"):
        AuthorityReceiptValidator(ROOT).verify(
            receipt,
            action="HUMAN_FEEDBACK",
            principal="human:alice",
            claim=claim,
        )


def test_authenticated_human_cannot_originate_policy_conflict(tmp_path: Path) -> None:
    store = _store(tmp_path)
    event = FeedbackIngestor(ROOT, store=store).capture(
        source_type="HUMAN_REVIEW",
        producer="policy-human",
        task_id="authority-policy-test",
        task_commit=_head(),
        severity="HIGH",
        message="A human assertion must not manufacture policy conflict authority.",
        category="POLICY_CONFLICT",
        stage_hint="RULE_RESOLUTION",
        value=_policy_proof(),
        captured_at="2026-08-14T02:00:00Z",
    )
    assert event["provenance"]["trust_status"] == "HUMAN_AUTHENTICATED"
    with pytest.raises(ValueError, match="canonical Adjudicator"):
        FindingNormalizer(ROOT, store=store).normalize(
            [event],
            generalized_problem="Conflicting policy obligations block one gate.",
            root_cause_class="POLICY_CONTRADICTION",
            repair_stages=["RULE_RESOLUTION"],
            closure_conditions=["The exact policy conflict is adjudicated."],
        )


def test_unsigned_execution_record_is_not_semantic_execution_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = ExecutionRecordBuilder(ROOT)
    record = {
        "schema_version": "1.0",
        "record_id": "rec_" + "1" * 64,
        "invocation_id": "inv_" + "2" * 64,
        "stage_id": "VERIFIER_BUILD",
        "role_id": "A5_VERIFIER_AUTHOR",
        "authority": {
            "task_id": "authority-execution-test",
            "task_commit": _head(),
            "control_plane_commit": _head(),
        },
        "task_lineage": {
            "input_task_commit": _head(),
            "output_task_commit": _head(),
            "task_changed": False,
        },
        "status": "VERIFIER_READY",
        "disposition": "ADVANCE",
        "outputs": {},
        "evidence_refs": [],
        "transition": {"action": "ADVANCE"},
        "validation": {},
    }
    monkeypatch.setattr(builder, "validate_persisted_record", lambda _record: record)
    with pytest.raises(ValueError, match="EXECUTION_RESULT requires an authenticated authority receipt"):
        builder.validate_execution_authority(record)


def test_active_lesson_requires_independent_curator_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path)
    finding_id = "finding_" + "a" * 64
    store.record_finding(
        {
            "finding_id": finding_id,
            "task_id": "lesson-task",
            "category": "BOUNDARY",
            "problem": {
                "generalized": "External effects were inferred from internal state.",
                "root_cause_class": "INTERNAL_PROXY",
            },
        }
    )
    validator = LearningIntegrityValidator(ROOT, store=store)
    _stub_learning_closure(monkeypatch, validator)
    lesson: dict[str, object] = {
        "schema_version": "1.0",
        "state": "ACTIVE",
        "category": "BOUNDARY",
        "failure_pattern": "External effects were inferred from internal state.",
        "root_cause_class": "INTERNAL_PROXY",
        "future_rule": "Verify the externally observable effect.",
        "targets": {
            "stages": ["VERIFIER_BUILD"],
            "roles": ["A5_VERIFIER_AUTHOR"],
            "domains": [],
        },
        "sources": [finding_id],
        "promotion": {
            "occurrences": 1,
            "distinct_tasks": 1,
            "policy_candidate": False,
        },
    }
    lesson["lesson_id"] = lesson_identity(lesson)
    with pytest.raises(ValueError, match="LESSON_ACTIVATION requires an authenticated authority receipt"):
        validator.validate_lesson(lesson)


def test_lesson_activation_receipt_cannot_cover_tampered_future_rule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path)
    finding_id = "finding_" + "b" * 64
    store.record_finding(
        {
            "finding_id": finding_id,
            "task_id": "lesson-task",
            "category": "BOUNDARY",
            "problem": {
                "generalized": "External effects were inferred from internal state.",
                "root_cause_class": "INTERNAL_PROXY",
            },
        }
    )
    validator = LearningIntegrityValidator(ROOT, store=store)
    _stub_learning_closure(monkeypatch, validator)
    lesson: dict[str, object] = {
        "schema_version": "1.0",
        "state": "ACTIVE",
        "category": "BOUNDARY",
        "failure_pattern": "External effects were inferred from internal state.",
        "root_cause_class": "INTERNAL_PROXY",
        "future_rule": "Verify the externally observable effect.",
        "targets": {
            "stages": ["VERIFIER_BUILD"],
            "roles": ["A5_VERIFIER_AUTHOR"],
            "domains": [],
        },
        "sources": [finding_id],
        "promotion": {
            "occurrences": 1,
            "distinct_tasks": 1,
            "policy_candidate": False,
        },
    }
    lesson["lesson_id"] = lesson_identity(lesson)
    lesson["authority_receipt"] = sign_receipt(
        "LESSON_ACTIVATION",
        "learning-curator",
        validator.lesson_activation_claim(lesson),
    )
    validator.validate_lesson(lesson)

    tampered = copy.deepcopy(lesson)
    tampered["future_rule"] = "Trust the internal counter and skip external verification."
    tampered["lesson_id"] = lesson_identity(tampered)
    with pytest.raises(ValueError, match="exact semantic action"):
        validator.validate_lesson(tampered)


def test_pattern_cannot_mix_unrelated_verified_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path)
    first = "finding_" + "c" * 64
    second = "finding_" + "d" * 64
    store.record_finding(
        {
            "finding_id": first,
            "task_id": "task-one",
            "category": "BOUNDARY",
            "problem": {"root_cause_class": "INTERNAL_PROXY"},
        }
    )
    store.record_finding(
        {
            "finding_id": second,
            "task_id": "task-two",
            "category": "UNRELATED",
            "problem": {"root_cause_class": "OTHER_ROOT_CAUSE"},
        }
    )
    validator = LearningIntegrityValidator(ROOT, store=store)
    _stub_learning_closure(monkeypatch, validator)
    pattern: dict[str, object] = {
        "schema_version": "1.0",
        "category": "BOUNDARY",
        "root_cause_class": "INTERNAL_PROXY",
        "lesson_ids": [],
        "finding_ids": [first, second],
        "task_ids": ["task-one", "task-two"],
        "occurrences": 2,
        "policy_candidate": False,
        "status": "ACTIVE",
    }
    pattern["pattern_id"] = pattern_identity(pattern)
    with pytest.raises(ValueError, match="category does not match source finding"):
        validator.validate_pattern(pattern)
