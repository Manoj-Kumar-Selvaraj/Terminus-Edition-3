from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from feedback.closure import FindingClosure  # noqa: E402
from feedback.ingestion import FeedbackIngestor  # noqa: E402
from feedback.normalizer import FindingNormalizer  # noqa: E402
from feedback.provenance import ProvenanceValidator  # noqa: E402
from feedback.registry import LearningStore  # noqa: E402
from remediation.planner import RemediationPlanner  # noqa: E402
from remediation.progress import RemediationProgressValidator  # noqa: E402
from remediation.router import RemediationInterlock  # noqa: E402

_SOURCE_FIXTURE = ".terminus/tests/fixtures/feedback_source_identities.json"


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


def _source_binding(identity: str) -> dict[str, str]:
    raw = (ROOT / _SOURCE_FIXTURE).read_bytes()
    return {
        "kind": "RESULT",
        "ref": f"git:{_head()}:{_SOURCE_FIXTURE}#{quote(identity, safe='')}",
        "content_hash": "sha256:" + hashlib.sha256(raw).hexdigest(),
    }


def _human_event(
    store: LearningStore,
    *,
    task_id: str = "feedback-test",
    category: str = "BOUNDARY",
    stage: str = "VERIFIER_BUILD",
    value: object | None = None,
) -> dict[str, Any]:
    return FeedbackIngestor(ROOT, store=store).capture(
        source_type="HUMAN_REVIEW",
        producer="cold-review-test",
        task_id=task_id,
        task_commit=_head(),
        severity="HIGH",
        message="Cold-review regression signal.",
        category=category,
        stage_hint=stage,
        value=value,
        captured_at="2026-08-14T00:00:00Z",
    )


def _finding(store: LearningStore, event: dict[str, Any]) -> dict[str, Any]:
    return FindingNormalizer(ROOT, store=store).normalize(
        [event],
        generalized_problem="A control-plane trust boundary must fail closed.",
        root_cause_class="TRUST_BOUNDARY_BYPASS",
        repair_stages=[str(event["observation"].get("stage_hint") or "VERIFIER_BUILD")],
        closure_conditions=["Independent canonical verification is current."],
        verification_owner="Q4_SPEC_TEST_CONTRACT_REVIEWER",
    )


def test_fbl_cold_001_pseudo_pass_cannot_authorize_closure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = ProvenanceValidator(ROOT)
    binding = {
        "kind": "RESULT",
        "ref": f"git:{_head()}:.terminus/reviews/feedback-test/pseudo.json",
        "content_hash": "sha256:" + "0" * 64,
    }
    monkeypatch.setattr(validator.evidence, "validate", lambda value, _index: dict(value))
    monkeypatch.setattr(validator, "_require_reachable", lambda _commit: None)
    monkeypatch.setattr(
        validator,
        "_git_json",
        lambda *_args: {
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


def test_fbl_cold_002_mark_repaired_requires_completed_post_floor_ledger(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    finding = _finding(store, _human_event(store))
    packet = RemediationPlanner(ROOT, store=store).plan(finding)
    with pytest.raises(ValueError, match="every planned remediation step"):
        FindingClosure(ROOT, store=store).mark_repaired(
            str(finding["finding_id"]),
            _head(),
            remediation_id=str(packet["remediation_id"]),
        )


def test_fbl_cold_002_progress_requires_declared_role_and_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    finding = _finding(store, _human_event(store))
    packet = RemediationPlanner(ROOT, store=store).plan(finding)
    output_commit = "1" * 40

    class FakeLedger:
        def __init__(self, _root: Path, _task_id: str):
            pass

        def load(self, *, validate_record_files: bool) -> list[dict[str, Any]]:
            assert validate_record_files is True
            return [
                {
                    "sequence": int(packet["ledger_sequence_floor"]) + 1,
                    "stage_id": "VERIFIER_BUILD",
                    "input_task_commit": packet["input_task_commit"],
                    "output_task_commit": output_commit,
                    "record_path": ".terminus/executions/fake.json",
                }
            ]

    monkeypatch.setattr("remediation.progress.ExecutionLedger", FakeLedger)
    validator = RemediationProgressValidator(ROOT, store=store)
    monkeypatch.setattr(
        validator,
        "_record",
        lambda _event: {
            "stage_id": "VERIFIER_BUILD",
            "role_id": "WRONG_ROLE",
            "disposition": "ADVANCE",
            "task_lineage": {
                "input_task_commit": packet["input_task_commit"],
                "output_task_commit": output_commit,
            },
        },
    )
    assert validator.progress(packet)["next_step"] is not None


def test_fbl_cold_003_repository_bytes_do_not_authenticate_wrong_source(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="exactly one event attestation"):
        FeedbackIngestor(ROOT, store=store).capture(
            source_type="PORTAL_CI",
            producer="portal-ci",
            task_id="feedback-source-spoof",
            task_commit=_head(),
            severity="HIGH",
            message="The fragment string alone must not authenticate Portal CI.",
            source_binding=_source_binding("repository-ci"),
        )


def test_fbl_cold_004_unreachable_side_commit_is_not_review_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = ProvenanceValidator(ROOT)
    binding = {
        "kind": "RESULT",
        "ref": f"git:{'0' * 40}:.terminus/reviews/feedback-test/fake.json",
        "content_hash": "sha256:" + "0" * 64,
    }
    monkeypatch.setattr(validator.evidence, "validate", lambda value, _index: dict(value))
    with pytest.raises(ValueError, match="authorized repository lineage"):
        validator.validate_review_result(
            binding=binding,
            producer="Q4_SPEC_TEST_CONTRACT_REVIEWER",
            task_id="feedback-test",
            task_commit=_head(),
            require_passing=True,
        )


def test_fbl_cold_005_automated_conflict_resolution_requires_semantic_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    first = _human_event(store, category="A")
    second = copy.deepcopy(first)
    second["feedback_id"] = "feedback_" + "1" * 64
    second["observation"]["category"] = "B"
    store.feedback.append(second)
    conflict = FindingNormalizer(ROOT, store=store).normalize(
        [first, second],
        generalized_problem="Conflicting classifications require adjudication.",
        root_cause_class="FEEDBACK_DISAGREEMENT",
        repair_stages=["RULE_RESOLUTION"],
        closure_conditions=["Conflict is explicitly resolved."],
    )
    resolution = copy.deepcopy(first)
    resolution["feedback_id"] = "feedback_" + "2" * 64
    resolution["source"] = {"type": "REVIEWER_REVIEW", "producer": "ADJUDICATOR"}
    resolution["observation"]["category"] = "CONFLICT_RESOLUTION"
    resolution["provenance"]["trust_status"] = "REPOSITORY_RESOLVED"
    resolution["provenance"]["source_binding"] = {
        "kind": "RESULT",
        "ref": f"git:{_head()}:.terminus/reviews/feedback-test/adjudication.json",
        "content_hash": "sha256:" + "0" * 64,
    }
    closure = FindingClosure(ROOT, store=store)
    called: dict[str, Any] = {}

    def reject(**kwargs: Any) -> dict[str, Any]:
        called.update(kwargs)
        raise ValueError("noncanonical conflict result")

    monkeypatch.setattr(closure.provenance, "validate_review_result", reject)
    with pytest.raises(ValueError, match="noncanonical conflict result"):
        closure.resolve_conflict(
            str(conflict["finding_id"]), resolution_feedback=[resolution]
        )
    assert called["conflict_resolution"] is True
    assert store.findings.get_latest("finding_id", str(conflict["finding_id"]))["state"] == "FEEDBACK_CONFLICT"


def test_fbl_cold_006_policy_conflict_is_canonical_and_interlocked(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    event = _human_event(
        store,
        category="POLICY_CONFLICT",
        stage="RULE_RESOLUTION",
        value={
            "conflicting_sources": [
                "TERMINUS_3_AI_INSTRUCTIONS.md",
                ".terminus/agents/PROTOCOL.md",
            ],
            "affected_gate": "RULE_RESOLUTION",
        },
    )
    finding = _finding(store, event)
    assert finding["state"] == "POLICY_CONFLICT"
    action = RemediationInterlock(ROOT, store=store).next_override(
        task_id="feedback-test", task_commit=_head()
    )
    assert action["action"] == "RESOLVE_POLICY_CONFLICT"
