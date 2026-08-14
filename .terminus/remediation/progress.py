"""Canonical remediation progress validation shared by router and closure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from execution.ledger import ExecutionLedger

from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator

from .planner import RemediationPlanner


class RemediationProgressValidator:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.planner = RemediationPlanner(self.root, store=self.store)

    def packet_for(
        self, *, finding_id: str, remediation_id: str | None = None
    ) -> dict[str, Any] | None:
        packets = [
            packet
            for packet in self.store.remediations.latest_by("remediation_id")
            if packet.get("finding_id") == finding_id
            and (
                remediation_id is None
                or packet.get("remediation_id") == remediation_id
            )
        ]
        if not packets:
            return None
        if remediation_id is None and len(packets) != 1:
            raise ValueError(
                "finding has multiple remediation packets; remediation_id is required"
            )
        packet = packets[-1]
        self._validate_canonical_packet(packet, finding_id=finding_id)
        return packet

    def progress(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        self.schemas.validate("remediation", packet)
        self._validate_canonical_packet(
            packet, finding_id=str(packet["finding_id"])
        )
        ledger = ExecutionLedger(self.root, str(packet["task_id"]))
        all_events = ledger.load(validate_record_files=True)
        floor = int(packet["ledger_sequence_floor"])
        if floor > len(all_events):
            raise ValueError(
                "remediation ledger_sequence_floor exceeds the durable execution ledger"
            )
        events = [event for event in all_events if int(event["sequence"]) > floor]
        cursor_commit = str(packet["input_task_commit"])
        minimum_sequence = floor
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
                if record.get("stage_id") != step["stage_id"]:
                    continue
                if record.get("role_id") != step["role_id"]:
                    continue
                if record.get("disposition") != "ADVANCE":
                    continue
                lineage = record.get("task_lineage")
                if not isinstance(lineage, Mapping):
                    continue
                if lineage.get("input_task_commit") != cursor_commit:
                    continue
                if lineage.get("output_task_commit") != event["output_task_commit"]:
                    continue
                if lineage.get("task_changed") is not True:
                    continue
                if not self._record_binds_remediation(record, packet, step):
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

    def require_complete(
        self,
        *,
        finding_id: str,
        remediation_id: str,
        repaired_task_commit: str,
    ) -> dict[str, Any]:
        packet = self.packet_for(
            finding_id=finding_id, remediation_id=remediation_id
        )
        if packet is None:
            raise ValueError(
                "REPAIRED transition requires an existing remediation packet"
            )
        progress = self.progress(packet)
        if progress["next_step"] is not None:
            raise ValueError(
                "REPAIRED transition requires every planned remediation step to ADVANCE"
            )
        terminal = str(progress["output_task_commit"])
        if terminal != repaired_task_commit:
            raise ValueError(
                "repaired_task_commit must equal the terminal remediation output commit"
            )
        if terminal == str(packet["input_task_commit"]):
            raise ValueError("REPAIRED transition requires a post-plan task commit")
        return packet

    def _validate_canonical_packet(
        self, packet: Mapping[str, Any], *, finding_id: str
    ) -> None:
        self.schemas.validate("remediation", packet)
        finding = self.store.findings.get_latest("finding_id", finding_id)
        if finding is None:
            raise ValueError("remediation packet references an unavailable finding")
        self.schemas.validate("finding", finding)
        expected = self.planner.expected_packet(
            finding,
            ledger_sequence_floor=int(packet["ledger_sequence_floor"]),
        )
        if dict(packet) != expected:
            raise ValueError(
                "remediation packet does not match canonical planner derivation"
            )

    def _record_binds_remediation(
        self,
        record: Mapping[str, Any],
        packet: Mapping[str, Any],
        step: Mapping[str, Any],
    ) -> bool:
        invocation = record.get("invocation_snapshot")
        if not isinstance(invocation, Mapping):
            return False
        learning = invocation.get("learning")
        if not isinstance(learning, Mapping):
            return False
        remediations = learning.get("remediations")
        if not isinstance(remediations, list):
            return False
        expected = RemediationPlanner.context_for_stage(
            packet, str(step["stage_id"])
        )
        if expected is None:
            return False
        return any(
            isinstance(item, Mapping) and dict(item) == expected
            for item in remediations
        )

    def _record(self, event: Mapping[str, Any]) -> dict[str, Any]:
        # Lazy import avoids the learning-context -> closure -> remediation cycle
        # while retaining full canonical replay at the consumption boundary.
        from execution.record import ExecutionRecordBuilder

        path = (self.root / str(event["record_path"])).resolve()
        if self.root not in path.parents:
            raise ValueError("remediation record path escapes repository root")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("remediation execution record must be an object")
        return ExecutionRecordBuilder(self.root).validate_persisted_record(value)
