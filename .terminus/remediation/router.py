"""Override normal workflow progression while task findings require repair/verification."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from feedback.closure import FindingClosure
from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator

from .progress import RemediationProgressValidator

_SEVERITY = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}


class RemediationInterlock:
    """Derive remediation actions without mutating normal workflow state."""

    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.progress = RemediationProgressValidator(self.root, store=self.store)

    def next_override(self, *, task_id: str, task_commit: str) -> dict[str, Any] | None:
        candidates = [
            finding
            for finding in self.store.findings.latest_by("finding_id")
            if finding.get("task_id") == task_id
            and finding.get("state") not in {"CLOSED", "WONT_FIX"}
        ]
        candidates.sort(
            key=lambda finding: (
                -_SEVERITY.get(str(finding.get("severity")), 0),
                str(finding.get("finding_id")),
            )
        )
        for finding in candidates:
            if not self._is_ancestor(str(finding["task_commit"]), task_commit):
                return {
                    "action": "REMEDIATION_LINEAGE_CONFLICT",
                    "finding_id": finding["finding_id"],
                    "finding_task_commit": finding["task_commit"],
                    "current_task_commit": task_commit,
                }
        findings = candidates
        if not findings:
            return None

        conflicts = [
            finding
            for finding in findings
            if finding["state"] in {"FEEDBACK_CONFLICT", "POLICY_CONFLICT"}
        ]
        if conflicts:
            finding = conflicts[0]
            return {
                "action": "RESOLVE_FEEDBACK_CONFLICT"
                if finding["state"] == "FEEDBACK_CONFLICT"
                else "RESOLVE_POLICY_CONFLICT",
                "finding_id": finding["finding_id"],
                "severity": finding["severity"],
                "task_commit": task_commit,
            }

        repairable = [
            finding for finding in findings if finding["state"] in {"OPEN", "ASSIGNED"}
        ]
        for finding in repairable:
            packet = self.progress.packet_for(finding_id=str(finding["finding_id"]))
            if packet is None:
                return {
                    "action": "PLAN_REMEDIATION",
                    "finding_id": finding["finding_id"],
                    "severity": finding["severity"],
                    "task_commit": task_commit,
                }
            progress = self.progress.progress(packet)
            if progress["next_step"] is not None:
                step = progress["next_step"]
                return {
                    "action": "REMEDIATE_STAGE",
                    "finding_id": finding["finding_id"],
                    "remediation_id": packet["remediation_id"],
                    "stage_id": step["stage_id"],
                    "primary_role_id": step["role_id"],
                    "step_ordinal": step["ordinal"],
                    "completed_steps": progress["completed_steps"],
                    "task_commit": task_commit,
                }
            return {
                "action": "MARK_REPAIRED_REQUIRED",
                "finding_id": finding["finding_id"],
                "remediation_id": packet["remediation_id"],
                "repaired_task_commit": progress["output_task_commit"],
            }

        repaired = [finding for finding in findings if finding["state"] == "REPAIRED"]
        if repaired:
            finding = repaired[0]
            return {
                "action": "AWAIT_REMEDIATION_VERIFICATION",
                "finding_id": finding["finding_id"],
                "verification_owner": finding["closure"]["verification_owner"],
                "remediation_id": finding["closure"].get("remediation_id"),
                "repaired_task_commit": finding["closure"].get("repaired_task_commit"),
            }

        verified = [finding for finding in findings if finding["state"] == "VERIFIED"]
        if verified:
            finding = verified[0]
            return {
                "action": "FINALIZE_REMEDIATION_CLOSURE",
                "finding_id": finding["finding_id"],
                "verification_owner": finding["closure"]["verification_owner"],
            }
        return None

    def on_record(self, *, task_id: str) -> list[dict[str, Any]]:
        """Auto-mark findings REPAIRED only through the canonical ledger validator."""
        updates: list[dict[str, Any]] = []
        findings = [
            finding
            for finding in self.store.findings.latest_by("finding_id")
            if finding.get("task_id") == task_id
            and finding.get("state") in {"OPEN", "ASSIGNED"}
        ]
        closure = FindingClosure(self.root, store=self.store)
        for finding in findings:
            packet = self.progress.packet_for(finding_id=str(finding["finding_id"]))
            if packet is None:
                continue
            progress = self.progress.progress(packet)
            if progress["next_step"] is None and progress["output_task_commit"]:
                updates.append(
                    closure.mark_repaired(
                        str(finding["finding_id"]),
                        str(progress["output_task_commit"]),
                        remediation_id=str(packet["remediation_id"]),
                    )
                )
        return updates

    def _is_ancestor(self, ancestor: str, descendant: str) -> bool:
        return (
            subprocess.run(
                ["git", "-C", str(self.root), "merge-base", "--is-ancestor", ancestor, descendant],
                capture_output=True,
            ).returncode
            == 0
        )
