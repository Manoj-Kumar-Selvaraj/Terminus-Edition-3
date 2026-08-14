from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from feedback.closure import FindingClosure  # noqa: E402
from feedback.ingestion import FeedbackIngestor  # noqa: E402
from feedback.normalizer import FindingNormalizer  # noqa: E402
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


def _store(tmp_path: Path) -> LearningStore:
    return LearningStore(
        ROOT,
        state_root=tmp_path / "state",
        knowledge_root=tmp_path / "knowledge",
    )


def _result_binding(path: str, identity: str) -> dict[str, str]:
    raw = (ROOT / path).read_bytes()
    return {
        "kind": "RESULT",
        "ref": f"git:{_head()}:{path}#{quote(identity, safe='')}",
        "content_hash": "sha256:" + hashlib.sha256(raw).hexdigest(),
    }


def _repaired_finding(
    store: LearningStore,
    *,
    verification_owner: str,
) -> dict[str, object]:
    commit = _head()
    initial_feedback = FeedbackIngestor(ROOT, store=store).capture(
        source_type="HUMAN_REVIEW",
        producer="closure-semantics-test",
        task_id=_TASK_ID,
        task_commit=commit,
        severity="HIGH",
        message="A repair requires independent verification before closure.",
        category="VERIFICATION_RESULT_SEMANTICS",
        stage_hint="VERIFIER_BUILD",
        captured_at="2026-08-14T00:00:00Z",
    )
    finding = FindingNormalizer(ROOT, store=store).normalize(
        [initial_feedback],
        generalized_problem="Closure must be authorized by the semantics of the bound reviewer result.",
        root_cause_class="UNBOUND_VERIFICATION_RESULT",
        repair_stages=["VERIFIER_BUILD"],
        should_have_been_caught_by=["SPEC_ALIGNMENT"],
        closure_conditions=["A current passing independent result verifies the repaired task commit."],
        verification_owner=verification_owner,
    )
    return FindingClosure(ROOT, store=store).mark_repaired(
        str(finding["finding_id"]), commit
    )


def _verification_feedback(
    store: LearningStore,
    *,
    producer: str,
    result_path: str,
) -> dict[str, object]:
    return FeedbackIngestor(ROOT, store=store).capture(
        source_type="INDEPENDENT_REVIEW",
        producer=producer,
        task_id=_TASK_ID,
        task_commit=_head(),
        severity="HIGH",
        message="This feedback claims the repaired finding is independently verified.",
        category="VERIFICATION_RESULT_SEMANTICS",
        stage_hint="VERIFIER_BUILD",
        source_binding=_result_binding(result_path, producer),
        captured_at="2026-08-14T00:00:00Z",
    )


def test_controlled_revise_result_cannot_close_finding(tmp_path: Path) -> None:
    store = _store(tmp_path)
    verifier = "Spec-Test Contract Reviewer"
    repaired = _repaired_finding(store, verification_owner=verifier)
    verification = _verification_feedback(
        store,
        producer=verifier,
        result_path=_Q4_REVISE_RESULT,
    )

    with pytest.raises(ValueError, match="passing outcome"):
        FindingClosure(ROOT, store=store).verify(
            str(repaired["finding_id"]),
            verifier_role=verifier,
            verification_feedback=[verification],
        )


def test_pre_repair_pass_result_cannot_verify_newer_task_commit(tmp_path: Path) -> None:
    store = _store(tmp_path)
    verifier = "Production Logic Auditor"
    repaired = _repaired_finding(store, verification_owner=verifier)
    verification = _verification_feedback(
        store,
        producer=verifier,
        result_path=_Q6_PASS_RESULT,
    )

    with pytest.raises(ValueError, match="verification task commit"):
        FindingClosure(ROOT, store=store).verify(
            str(repaired["finding_id"]),
            verifier_role=verifier,
            verification_feedback=[verification],
        )
