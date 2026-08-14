"""Plan controlled multi-stage repairs from canonical findings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from execution.authority import ExecutionAuthority
from execution.ledger import ExecutionLedger
from retrieval.policy import RetrievalPolicy

from feedback.model import stable_id
from feedback.normalizer import FindingNormalizer
from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator

_DEFAULT_PROHIBITED = [
    "Do not edit or suppress the detector that exposed the finding merely to make the check pass.",
    "Do not fabricate evidence, reviewer closure, CI success, model results, or task commits.",
    "Do not let a repair agent close its own finding; closure requires independent verification.",
    "Do not broaden reviewer access to raw historical findings when generalized lessons are sufficient.",
]


class RemediationPlanner:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.policy = RetrievalPolicy(self.root)
        self.authority = ExecutionAuthority(self.policy)
        self.normalizer = FindingNormalizer(self.root, store=self.store)
        contract = json.loads(
            (self.root / ".terminus" / "agents" / "stage_contracts.json").read_text(
                encoding="utf-8"
            )
        )
        self.stage_order = {
            stage["id"]: index for index, stage in enumerate(contract["stages"])
        }

    def plan(self, finding: Mapping[str, Any]) -> dict[str, Any]:
        """Create the one canonical packet for the current finding/ledger point."""
        finding = self.normalizer.validate_persisted_finding(finding)
        if finding["state"] in {"CLOSED", "VERIFIED", "WONT_FIX"}:
            raise ValueError("closed/verified findings do not require a remediation plan")
        if finding["state"] in {"FEEDBACK_CONFLICT", "POLICY_CONFLICT"}:
            raise ValueError("conflicted findings must be resolved before remediation planning")
        ledger = ExecutionLedger(self.root, str(finding["task_id"]))
        sequence_floor = len(ledger.load(validate_record_files=True))
        packet = self.expected_packet(
            finding,
            ledger_sequence_floor=sequence_floor,
        )
        self.schemas.validate("remediation", packet)
        self.store.record_remediation(packet)
        return packet

    def expected_packet(
        self,
        finding: Mapping[str, Any],
        *,
        ledger_sequence_floor: int,
    ) -> dict[str, Any]:
        """Deterministically derive every planner-owned packet field."""
        finding = self.normalizer.validate_persisted_finding(finding)
        if not isinstance(ledger_sequence_floor, int) or isinstance(
            ledger_sequence_floor, bool
        ) or ledger_sequence_floor < 0:
            raise ValueError("ledger_sequence_floor must be a non-negative integer")
        stages = sorted(
            finding["ownership"]["repair_stages"],
            key=lambda stage_id: self.stage_order.get(stage_id, 10_000),
        )
        steps = []
        for ordinal, stage_id in enumerate(stages, start=1):
            if stage_id not in self.policy.stages:
                raise ValueError(f"unregistered repair stage: {stage_id}")
            role_id = self.authority.primary_role_for_stage(stage_id)
            steps.append(
                {
                    "ordinal": ordinal,
                    "stage_id": stage_id,
                    "role_id": role_id,
                    "responsibility": f"Repair {finding['category']} at its owning lifecycle boundary.",
                    "required_behavior": finding["problem"]["generalized"],
                    "closure_conditions": list(finding["closure"]["conditions"]),
                }
            )
        packet: dict[str, Any] = {
            "schema_version": "1.0",
            "finding_id": finding["finding_id"],
            "task_id": finding["task_id"],
            "input_task_commit": finding["task_commit"],
            "ledger_sequence_floor": ledger_sequence_floor,
            "steps": steps,
            "closure_owner": finding["closure"]["verification_owner"],
            "prohibited_shortcuts": list(_DEFAULT_PROHIBITED),
        }
        packet["remediation_id"] = stable_id("remediation", packet)
        return packet

    @staticmethod
    def context_for_stage(
        packet: Mapping[str, Any], stage_id: str
    ) -> dict[str, Any] | None:
        for step in packet["steps"]:
            if step["stage_id"] == stage_id:
                return {
                    "remediation_id": packet["remediation_id"],
                    "finding_id": packet["finding_id"],
                    "responsibility": step["responsibility"],
                    "required_behavior": step["required_behavior"],
                    "closure_conditions": list(step["closure_conditions"]),
                    "prohibited_shortcuts": list(packet["prohibited_shortcuts"]),
                }
        return None
