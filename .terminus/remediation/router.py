"""Override normal workflow progression while task findings require repair/verification."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from execution.ledger import ExecutionLedger

from feedback.closure import FindingClosure
from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator

_SEVERITY = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}


class RemediationInterlock:
    """Derive remediation actions without mutating normal workflow state."""

    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)

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
            packet = self._packet_for(finding["finding_id"])
            if packet is None:
                return {
                    "action": "PLAN_REMEDIATION",
                    "finding_id": finding["finding_id"],
                    "severity": finding["severity"],
                    "task_commit": task_commit,
                }
            progress = self._progress(packet)
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
        """Auto-mark findings REPAIRED after every planned repair step has ADVANCED."""
        updates: list[dict[str, Any]] = []
        findings = [
            finding
            for finding in self.store.findings.latest_by("finding_id")
            if finding.get("task_id") == task_id
            and finding.get("state") in {"OPEN", "ASSIGNED"}
        ]
        closure = FindingClosure(self.root, store=self.store)
        for finding in findings:
            packet = self._packet_for(finding["finding_id"])
            if packet is None:
                continue
            progress = self._progress(packet)
            if progress["next_step"] is None and progress["output_task_commit"]:
                updates.append(
                    closure.mark_repaired(
                        finding["finding_id"], str(progress["output_task_commit"])
                    )
                )
        return updates

    def _packet_for(self, finding_id: str) -> dict[str, Any] | None:
        packets = [
            packet
            for packet in self.store.remediations.latest_by("remediation_id")
            if packet.get("finding_id") == finding_id
        ]
        if not packets:
            return None
        packet = packets[-1]
        self.schemas.validate("remediation", packet)
        return packet

    def _progress(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        ledger = ExecutionLedger(self.root, str(packet["task_id"]))
        events = [
            event
            for event in ledger.load(validate_record_files=True)
            if int(event["sequence"]) > int(packet["ledger_sequence_floor"])
        ]
        cursor_commit = str(packet["input_task_commit"])
        minimum_sequence = int(packet["ledger_sequence_floor"])
        completed: list[int] = []
        for step in packet["steps"]:
            match = None
            for event in events:
                if int(event["sequence"]) <= minimum_sequence:
                    continue
                if event["stage_id"] != step["stage_id"]:
                    continue
                if event["input_task_commit"] != cursor_commit:
                    continue
                record = self._record(event)
                if record.get("disposition") != "ADVANCE":
                    continue
                match = (event, record)
                break
            if match is None:
                return {
                    "completed_steps": completed,
                    "next_step": dict(step),
                    "output_task_commit": cursor_commit,
                }
            event, _record = match
            completed.append(int(step["ordinal"]))
            minimum_sequence = int(event["sequence"])
            cursor_commit = str(event["output_task_commit"])
        return {
            "completed_steps": completed,
            "next_step": None,
            "output_task_commit": cursor_commit,
        }

    def _record(self, event: Mapping[str, Any]) -> dict[str, Any]:
        path = (self.root / str(event["record_path"])).resolve()
        if self.root not in path.parents:
            raise ValueError("remediation record path escapes repository root")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("remediation execution record must be an object")
        return value

    def _is_ancestor(self, ancestor: str, descendant: str) -> bool:
        return (
            subprocess.run(
                ["git", "-C", str(self.root), "merge-base", "--is-ancestor", ancestor, descendant],
                capture_output=True,
            ).returncode
            == 0
        )
