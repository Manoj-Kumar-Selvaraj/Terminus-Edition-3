"""Append-only finding state transitions with independent verification."""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .model import FindingState, finding_identity
from .registry import LearningStore
from .schema_validation import LearningSchemaValidator


class FindingClosure:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)

    def mark_repaired(self, finding_id: str, repaired_task_commit: str) -> dict[str, Any]:
        finding = self._latest(finding_id)
        if finding["state"] not in {"OPEN", "ASSIGNED", "FEEDBACK_CONFLICT"}:
            raise ValueError(f"finding cannot move to REPAIRED from {finding['state']}")
        self._require_descendant(finding["task_commit"], repaired_task_commit)
        updated = copy.deepcopy(finding)
        updated["state"] = FindingState.REPAIRED.value
        updated["closure"]["repaired_task_commit"] = repaired_task_commit
        self._append_same_identity(updated, finding_id)
        return updated

    def verify(
        self,
        finding_id: str,
        *,
        verifier_role: str,
        verification_feedback: list[Mapping[str, Any]],
        close: bool = True,
    ) -> dict[str, Any]:
        finding = self._latest(finding_id)
        if finding["state"] != "REPAIRED":
            raise ValueError("only REPAIRED findings can be independently verified")
        if verifier_role in set(finding["ownership"]["repair_roles"]):
            raise ValueError("a repair owner cannot verify its own finding")
        if verifier_role != finding["closure"]["verification_owner"]:
            raise ValueError(
                "verification role does not match finding closure verification_owner"
            )
        repaired_commit = finding["closure"].get("repaired_task_commit")
        if not repaired_commit:
            raise ValueError("REPAIRED finding is missing repaired_task_commit")
        feedback_ids: list[str] = []
        for event in verification_feedback:
            self.schemas.validate("feedback", event)
            if event["task"]["task_id"] != finding["task_id"]:
                raise ValueError("verification feedback belongs to another task")
            self._require_descendant(repaired_commit, event["task"]["task_commit"])
            feedback_ids.append(str(event["feedback_id"]))
        if not feedback_ids:
            raise ValueError("verification requires at least one feedback event")
        updated = copy.deepcopy(finding)
        updated["state"] = FindingState.CLOSED.value if close else FindingState.VERIFIED.value
        updated["closure"]["verified_by_feedback"] = list(dict.fromkeys(feedback_ids))
        self._append_same_identity(updated, finding_id)
        return updated

    def _latest(self, finding_id: str) -> dict[str, Any]:
        finding = self.store.findings.get_latest("finding_id", finding_id)
        if finding is None:
            raise ValueError(f"unknown finding_id: {finding_id}")
        self.schemas.validate("finding", finding)
        return finding

    def _append_same_identity(self, finding: dict[str, Any], expected_id: str) -> None:
        if finding_identity(finding) != expected_id:
            raise ValueError("finding semantic identity changed during state transition")
        self.schemas.validate("finding", finding)
        self.store.findings.append(finding)

    def _require_descendant(self, ancestor: str, descendant: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "merge-base", "--is-ancestor", ancestor, descendant],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(
                f"task commit {descendant} is not a descendant of required commit {ancestor}"
            )
