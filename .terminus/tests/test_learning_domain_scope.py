from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from feedback.model import lesson_identity  # noqa: E402
from feedback.registry import LearningStore  # noqa: E402
from learning.projection import LearningProjector  # noqa: E402


def test_domain_scoped_lesson_requires_explicit_matching_domain(tmp_path: Path) -> None:
    store = LearningStore(
        ROOT,
        state_root=tmp_path / "state",
        knowledge_root=tmp_path / "knowledge",
    )
    lesson: dict[str, object] = {
        "schema_version": "1.0",
        "state": "ACTIVE",
        "category": "DOMAIN_BOUNDARY",
        "failure_pattern": "A domain-specific invariant was applied outside its intended domain.",
        "root_cause_class": "DOMAIN_SCOPE_LEAK",
        "future_rule": "Apply this invariant only when the invocation explicitly identifies the matching domain.",
        "targets": {
            "stages": ["VERIFIER_BUILD"],
            "roles": ["A5_VERIFIER_AUTHOR"],
            "domains": ["jetstream"],
        },
        "sources": ["finding_" + "0" * 64],
        "promotion": {
            "occurrences": 1,
            "distinct_tasks": 1,
            "policy_candidate": False,
        },
    }
    lesson["lesson_id"] = lesson_identity(lesson)
    store.lessons.append(lesson)

    projector = LearningProjector(ROOT, store=store)
    assert projector.project(
        stage_id="VERIFIER_BUILD",
        role_id="A5_VERIFIER_AUTHOR",
    )["lesson_count"] == 0
    assert projector.project(
        stage_id="VERIFIER_BUILD",
        role_id="A5_VERIFIER_AUTHOR",
        domain="postgresql",
    )["lesson_count"] == 0
    assert projector.project(
        stage_id="VERIFIER_BUILD",
        role_id="A5_VERIFIER_AUTHOR",
        domain="jetstream",
    )["lesson_count"] == 1
