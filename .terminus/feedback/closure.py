"""Append-only finding state transitions with independent verification."""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from typing import Any, Mapping

from remediation.progress import RemediationProgressValidator

from .model import FindingState, content_hash, finding_identity
from .provenance import ProvenanceValidator
from .registry import LearningStore
from .schema_validation import LearningSchemaValidator

_CONFLICT_RESOLVERS = frozenset({"ADJUDICATOR"})


class FindingClosure:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.provenance = ProvenanceValidator(self.root)
        self.remediation = RemediationProgressValidator(
            self.root, store=self.store
        )

    def mark_repaired(
        self,
        finding_id: str,
        repaired_task_commit: str,
        *,
        remediation_id: str,
    ) -> dict[str, Any]:
        """Move to REPAIRED only after the bound remediation ledger is complete."""
        finding = self._latest(finding_id)
        if finding["state"] not in {"OPEN", "ASSIGNED"}:
            raise ValueError(
                f"finding cannot move to REPAIRED from {finding['state']}"
            )
        self._require_descendant(finding["task_commit"], repaired_task_commit)
        packet = self.remediation.require_complete(
            finding_id=finding_id,
            remediation_id=remediation_id,
            repaired_task_commit=repaired_task_commit,
        )
        if packet["task_id"] != finding["task_id"]:
            raise ValueError("remediation packet belongs to another task")
        if packet["input_task_commit"] != finding["task_commit"]:
            raise ValueError("remediation packet does not bind the finding snapshot")
        updated = copy.deepcopy(finding)
        updated["state"] = FindingState.REPAIRED.value
        updated["closure"]["repaired_task_commit"] = repaired_task_commit
        updated["closure"]["remediation_id"] = remediation_id
        self._append_same_identity(updated, finding_id)
        return updated

    def resolve_conflict(
        self,
        finding_id: str,
        *,
        resolution_feedback: list[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Retire a conflict only after evidence resolves this exact finding."""
        finding = self._latest(finding_id)
        if finding["state"] not in {"FEEDBACK_CONFLICT", "POLICY_CONFLICT"}:
            raise ValueError(
                "only feedback/policy conflicts can use conflict resolution"
            )
        binding = self._conflict_binding(finding)
        feedback_ids: list[str] = []
        for event in resolution_feedback:
            self._validate_conflict_resolution_event(
                finding,
                event,
                conflict_binding=binding,
            )
            feedback_ids.append(str(event["feedback_id"]))
        if not feedback_ids:
            raise ValueError(
                "conflict resolution requires at least one trusted feedback event"
            )
        updated = copy.deepcopy(finding)
        updated["state"] = FindingState.WONT_FIX.value
        updated["closure"]["verified_by_feedback"] = list(
            dict.fromkeys(feedback_ids)
        )
        self._append_same_identity(updated, finding_id)
        self.assert_conflict_resolved(updated)
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
            raise ValueError(
                "only REPAIRED findings can be independently verified"
            )
        if verifier_role in set(finding["ownership"]["repair_roles"]):
            raise ValueError("a repair owner cannot verify its own finding")
        if verifier_role != finding["closure"]["verification_owner"]:
            raise ValueError(
                "verification role does not match finding closure verification_owner"
            )
        repaired_commit = finding["closure"].get("repaired_task_commit")
        remediation_id = finding["closure"].get("remediation_id")
        if not isinstance(repaired_commit, str) or not repaired_commit:
            raise ValueError("REPAIRED finding is missing repaired_task_commit")
        if not isinstance(remediation_id, str) or not remediation_id:
            raise ValueError("REPAIRED finding is missing remediation_id")
        self.remediation.require_complete(
            finding_id=finding_id,
            remediation_id=remediation_id,
            repaired_task_commit=repaired_commit,
        )
        feedback_ids: list[str] = []
        for event in verification_feedback:
            self._validate_verification_event(
                finding,
                event,
                verifier_role=verifier_role,
                repaired_commit=repaired_commit,
            )
            feedback_ids.append(str(event["feedback_id"]))
        if not feedback_ids:
            raise ValueError("verification requires at least one feedback event")
        updated = copy.deepcopy(finding)
        updated["state"] = (
            FindingState.CLOSED.value if close else FindingState.VERIFIED.value
        )
        updated["closure"]["verified_by_feedback"] = list(
            dict.fromkeys(feedback_ids)
        )
        self._append_same_identity(updated, finding_id)
        self.assert_learning_eligible(updated)
        return updated

    def assert_repaired_authorized(self, finding: Mapping[str, Any]) -> None:
        """Replay the exact remediation proof for a persisted REPAIRED row."""
        self.schemas.validate("finding", finding)
        if finding.get("state") != "REPAIRED":
            raise ValueError("finding is not in REPAIRED state")
        repaired_commit = finding["closure"].get("repaired_task_commit")
        remediation_id = finding["closure"].get("remediation_id")
        if not isinstance(repaired_commit, str) or not repaired_commit:
            raise ValueError("REPAIRED finding is missing repaired_task_commit")
        if not isinstance(remediation_id, str) or not remediation_id:
            raise ValueError("REPAIRED finding is missing remediation_id")
        self.remediation.require_complete(
            finding_id=str(finding["finding_id"]),
            remediation_id=remediation_id,
            repaired_task_commit=repaired_commit,
        )

    def assert_learning_eligible(self, finding: Mapping[str, Any]) -> None:
        """Replay both remediation and closure evidence before learning."""
        self.schemas.validate("finding", finding)
        if finding.get("state") not in {"VERIFIED", "CLOSED"}:
            raise ValueError("finding is not independently verified/closed")
        repaired_commit = finding["closure"].get("repaired_task_commit")
        remediation_id = finding["closure"].get("remediation_id")
        if not isinstance(repaired_commit, str) or not repaired_commit:
            raise ValueError("verified finding is missing repaired_task_commit")
        if not isinstance(remediation_id, str) or not remediation_id:
            raise ValueError("verified finding is missing remediation_id")
        self.remediation.require_complete(
            finding_id=str(finding["finding_id"]),
            remediation_id=remediation_id,
            repaired_task_commit=repaired_commit,
        )
        verifier_role = str(finding["closure"]["verification_owner"])
        feedback_ids = finding["closure"].get("verified_by_feedback", [])
        if not isinstance(feedback_ids, list) or not feedback_ids:
            raise ValueError("verified finding is missing verification feedback")
        for feedback_id in feedback_ids:
            event = self.store.feedback.get_latest(
                "feedback_id", str(feedback_id)
            )
            if event is None:
                raise ValueError(
                    f"verified finding references unavailable feedback: {feedback_id}"
                )
            self._validate_verification_event(
                finding,
                event,
                verifier_role=verifier_role,
                repaired_commit=repaired_commit,
            )

    def assert_conflict_resolved(self, finding: Mapping[str, Any]) -> None:
        """Replay exact conflict-resolution authority for a WONT_FIX row."""
        self.schemas.validate("finding", finding)
        if finding.get("state") != "WONT_FIX":
            raise ValueError("finding is not a resolved conflict")
        feedback_ids = finding["closure"].get("verified_by_feedback", [])
        if not isinstance(feedback_ids, list) or not feedback_ids:
            raise ValueError("resolved conflict is missing resolution feedback")
        binding = self._conflict_binding(finding)
        for feedback_id in feedback_ids:
            event = self.store.feedback.get_latest(
                "feedback_id", str(feedback_id)
            )
            if event is None:
                raise ValueError(
                    f"resolved conflict references unavailable feedback: {feedback_id}"
                )
            self._validate_conflict_resolution_event(
                finding,
                event,
                conflict_binding=binding,
            )

    def _validate_verification_event(
        self,
        finding: Mapping[str, Any],
        event: Mapping[str, Any],
        *,
        verifier_role: str,
        repaired_commit: str,
    ) -> None:
        self.schemas.validate("feedback", event)
        if event["task"]["task_id"] != finding["task_id"]:
            raise ValueError("verification feedback belongs to another task")
        verification_task_commit = str(event["task"]["task_commit"])
        if verification_task_commit != repaired_commit:
            raise ValueError(
                "verification feedback must bind the exact repaired_task_commit"
            )
        source = event["source"]
        provenance = event["provenance"]
        if verifier_role == "HUMAN_REVIEWER":
            if (
                source["type"] != "HUMAN_REVIEW"
                or provenance["trust_status"] != "HUMAN_ASSERTED"
            ):
                raise ValueError(
                    "human closure requires HUMAN_REVIEW asserted feedback"
                )
            return
        if provenance["trust_status"] != "REPOSITORY_RESOLVED":
            raise ValueError(
                "verification feedback must resolve to canonical repository review evidence"
            )
        if source["producer"] != verifier_role:
            raise ValueError(
                "verification feedback producer does not match verification owner"
            )
        binding = provenance.get("source_binding")
        if not isinstance(binding, Mapping):
            raise ValueError(
                "verification feedback is missing canonical RESULT evidence"
            )
        self.provenance.validate_review_result(
            binding=binding,
            producer=verifier_role,
            task_id=str(finding["task_id"]),
            task_commit=repaired_commit,
            require_passing=True,
        )

    def _validate_conflict_resolution_event(
        self,
        finding: Mapping[str, Any],
        event: Mapping[str, Any],
        *,
        conflict_binding: Mapping[str, Any],
    ) -> None:
        self.schemas.validate("feedback", event)
        if event["task"]["task_id"] != finding["task_id"]:
            raise ValueError("conflict resolution feedback belongs to another task")
        if str(event["task"]["task_commit"]) != str(finding["task_commit"]):
            raise ValueError(
                "conflict resolution must bind the exact conflicted task snapshot"
            )
        if event["observation"].get("category") != "CONFLICT_RESOLUTION":
            raise ValueError(
                "conflict resolution feedback must be explicitly classified"
            )
        detail = event["observation"].get("value")
        if not isinstance(detail, Mapping):
            raise ValueError(
                "conflict resolution feedback requires structured observation.value"
            )
        expected_detail = {**dict(conflict_binding), "resolution": "RESOLVED"}
        if dict(detail) != expected_detail:
            raise ValueError(
                "conflict resolution evidence is not bound to this exact conflict"
            )
        source = event["source"]
        provenance = event["provenance"]
        if (
            source["type"] == "HUMAN_REVIEW"
            and provenance["trust_status"] == "HUMAN_ASSERTED"
        ):
            return
        producer = str(source["producer"])
        if producer not in _CONFLICT_RESOLVERS:
            raise ValueError(
                "automated semantic conflict resolution requires the Adjudicator"
            )
        if provenance["trust_status"] != "REPOSITORY_RESOLVED":
            raise ValueError(
                "automated conflict resolution must resolve to repository evidence"
            )
        source_binding = provenance.get("source_binding")
        if not isinstance(source_binding, Mapping):
            raise ValueError(
                "conflict resolution is missing canonical RESULT evidence"
            )
        self.provenance.validate_review_result(
            binding=source_binding,
            producer=producer,
            task_id=str(finding["task_id"]),
            task_commit=str(finding["task_commit"]),
            require_passing=True,
            conflict_resolution=True,
            conflict_binding=conflict_binding,
        )

    def _conflict_binding(self, finding: Mapping[str, Any]) -> dict[str, Any]:
        original_state = str(finding.get("state"))
        if original_state == "WONT_FIX":
            if finding.get("category") == "POLICY_CONFLICT":
                conflict_type = "POLICY_CONFLICT"
            elif finding.get("category") == "FEEDBACK_CONFLICT":
                conflict_type = "FEEDBACK_CONFLICT"
            else:
                # Historic WONT_FIX rows are not allowed to manufacture a new
                # conflict type; the finding identity retains category/signals.
                conflict_type = str(finding.get("category"))
        else:
            conflict_type = original_state
        if conflict_type not in {"FEEDBACK_CONFLICT", "POLICY_CONFLICT"}:
            raise ValueError("finding does not encode a canonical conflict type")
        signals = [str(item) for item in finding.get("signals", [])]
        if not signals:
            raise ValueError("conflict finding is missing original signal IDs")
        categories: set[str] = set()
        claims: list[dict[str, Any]] = []
        affected_gates: set[str] = set()
        policy_rule_hashes: set[str] = set()
        for feedback_id in signals:
            event = self.store.feedback.get_latest("feedback_id", feedback_id)
            if event is None:
                raise ValueError(
                    f"conflict finding references unavailable signal: {feedback_id}"
                )
            self.schemas.validate("feedback", event)
            if event["task"]["task_id"] != finding["task_id"] or str(
                event["task"]["task_commit"]
            ) != str(finding["task_commit"]):
                raise ValueError(
                    "conflict source signal does not bind the finding task snapshot"
                )
            category = str(event["observation"].get("category", "UNCLASSIFIED"))
            categories.add(category)
            value = event["observation"].get("value")
            claims.append(
                {
                    "feedback_id": feedback_id,
                    "category": category,
                    "claim_hash": content_hash(value),
                }
            )
            if conflict_type == "POLICY_CONFLICT" and isinstance(value, Mapping):
                gate = value.get("affected_gate")
                if isinstance(gate, str):
                    affected_gates.add(gate)
                rules = value.get("rules")
                if isinstance(rules, list):
                    for rule in rules:
                        if isinstance(rule, Mapping) and isinstance(
                            rule.get("rule_hash"), str
                        ):
                            policy_rule_hashes.add(str(rule["rule_hash"]))
        binding: dict[str, Any] = {
            "finding_id": str(finding["finding_id"]),
            "conflict_type": conflict_type,
            "signal_ids": sorted(signals),
            "signal_claims": sorted(
                claims, key=lambda item: str(item["feedback_id"])
            ),
            "conflicting_categories": sorted(categories),
        }
        if conflict_type == "POLICY_CONFLICT":
            if len(affected_gates) != 1 or len(policy_rule_hashes) < 2:
                raise ValueError(
                    "policy conflict lacks one affected gate and two exact rule hashes"
                )
            binding["affected_gate"] = next(iter(affected_gates))
            binding["policy_rule_hashes"] = sorted(policy_rule_hashes)
        return binding

    def _latest(self, finding_id: str) -> dict[str, Any]:
        finding = self.store.findings.get_latest("finding_id", finding_id)
        if finding is None:
            raise ValueError(f"unknown finding_id: {finding_id}")
        self.schemas.validate("finding", finding)
        return finding

    def _append_same_identity(
        self, finding: dict[str, Any], expected_id: str
    ) -> None:
        if finding_identity(finding) != expected_id:
            raise ValueError(
                "finding semantic identity changed during state transition"
            )
        self.schemas.validate("finding", finding)
        self.store.record_finding(finding)

    def _require_descendant(self, ancestor: str, descendant: str) -> None:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "merge-base",
                "--is-ancestor",
                ancestor,
                descendant,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(
                f"task commit {descendant} is not a descendant of required commit {ancestor}"
            )
