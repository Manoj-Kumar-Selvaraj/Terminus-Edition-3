"""Canonical execution-record builder with fail-closed evidence resolution."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from learning.context import LearningContextBuilder
from retrieval.policy import RetrievalPolicy

from . import record_core as _core
from .evidence_refs import EvidenceReferenceVerifier
from .handoff_contract import accepted_handoff_ids

_SHA = _core._SHA
_SHA256 = _core._SHA256
_EVIDENCE_KINDS = _core._EVIDENCE_KINDS
_TASK_MUTATING_ROLE_CLASSES = _core._TASK_MUTATING_ROLE_CLASSES
_EVIDENCE_SENSITIVE_STAGES = _core._EVIDENCE_SENSITIVE_STAGES


class ExecutionRecordBuilder(_core.ExecutionRecordBuilder):
    """Extend the core recorder with evidence, handoff and learning provenance."""

    def __init__(self, root: Path, policy: RetrievalPolicy | None = None):
        super().__init__(root, policy)
        self.evidence_ref_verifier = EvidenceReferenceVerifier(self.root)
        self.learning_context = LearningContextBuilder(self.root)

    def build(
        self,
        invocation: Mapping[str, Any],
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        handoff_id = result.get("handoff_id")
        if handoff_id is not None and (
            not isinstance(handoff_id, str) or not handoff_id.startswith("handoff_")
        ):
            raise ValueError("stage result handoff_id is invalid")
        core_result = dict(result)
        core_result.pop("handoff_id", None)
        record = super().build(invocation, core_result)
        mutable = dict(record)
        mutable.pop("record_id", None)
        mutable["invocation_snapshot"] = self._json_copy(invocation)
        if handoff_id is not None:
            if handoff_id not in accepted_handoff_ids(invocation):
                raise ValueError(
                    "stage result handoff_id does not match a canonical executor handoff for this invocation"
                )
            mutable["handoff_id"] = handoff_id
        mutable["record_id"] = self._record_id(mutable)
        return self._ordered_record(mutable)

    def validate_persisted_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Replay a durable record through the canonical invocation/result builder."""
        value = self._json_copy(record)
        invocation = value.get("invocation_snapshot")
        if not isinstance(invocation, Mapping):
            raise ValueError(
                "durable execution record is missing canonical invocation_snapshot"
            )
        lineage = value.get("task_lineage")
        if not isinstance(lineage, Mapping):
            raise ValueError("durable execution record has invalid task_lineage")
        result: dict[str, Any] = {
            "schema_version": "1.0",
            "invocation_id": value.get("invocation_id"),
            "output_task_commit": lineage.get("output_task_commit"),
            "status": value.get("status"),
            "outputs": value.get("outputs"),
            "evidence_refs": value.get("evidence_refs"),
        }
        if "handoff_id" in value:
            result["handoff_id"] = value["handoff_id"]
        if "route_key" in value:
            result["route_key"] = value["route_key"]
        if "blocking_reason" in value:
            result["blocking_reason"] = value["blocking_reason"]
        rebuilt = self.build(invocation, result)
        if rebuilt != value:
            raise ValueError(
                "durable execution record does not reproduce from its canonical invocation/result"
            )
        return rebuilt

    @staticmethod
    def _json_copy(value: Mapping[str, Any]) -> dict[str, Any]:
        try:
            copied = json.loads(
                json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("execution object must be JSON-compatible") from exc
        if not isinstance(copied, dict):
            raise ValueError("execution object must be one JSON object")
        return copied

    def _validate_invocation(self, invocation: Mapping[str, Any]) -> dict[str, Any]:
        packet = super()._validate_invocation(invocation)
        learning = packet.get("learning")
        if not isinstance(learning, Mapping):
            raise ValueError("invocation is missing canonical learning context")
        authority = packet["authority"]
        stage = packet["stage"]
        self.learning_context.validate_projection(
            learning,
            stage_id=str(stage["stage_id"]),
            role_id=str(stage["role_id"]),
            task_id=authority.get("task_id"),
            task_commit=authority.get("task_commit"),
        )
        return packet

    def _validate_task_lineage(
        self, invocation: Mapping[str, Any], output_task_commit: str
    ) -> dict[str, Any]:
        lineage = super()._validate_task_lineage(invocation, output_task_commit)
        if not lineage["task_changed"]:
            return lineage
        task_id = str(invocation["authority"]["task_id"])
        input_task_commit = str(lineage["input_task_commit"])
        changed = subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "diff",
                "--name-only",
                "--no-renames",
                input_task_commit,
                output_task_commit,
                "--",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        forbidden = [
            path
            for path in changed
            if path and not self._task_mutation_path_allowed(task_id, path)
        ]
        if forbidden:
            raise ValueError(
                "task producer/fixer output modifies protected repository paths: "
                + ", ".join(sorted(forbidden))
            )
        if not changed:
            raise ValueError(
                "task producer/fixer output commit must contain an authorized task-scope change"
            )
        return lineage

    @staticmethod
    def _task_mutation_path_allowed(task_id: str, path: str) -> bool:
        if path.startswith(f"{task_id}/"):
            return True
        if path == f".terminus/designs/{task_id}.json":
            return True
        if path.startswith(f".terminus/designs/{task_id}-"):
            return True
        if path.startswith(f".terminus/designs/{task_id}/"):
            return True
        return path.startswith(f".terminus/contracts/{task_id}/")

    def _validate_evidence_refs(self, values: list[Any]) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for index, value in enumerate(values):
            if not isinstance(value, dict):
                raise ValueError(f"evidence_refs[{index}] must be an object")
            unknown = set(value) - {"kind", "ref", "content_hash"}
            if unknown:
                raise ValueError(
                    f"evidence_refs[{index}] has unknown fields: {sorted(unknown)}"
                )
            if value.get("kind") not in _EVIDENCE_KINDS:
                raise ValueError(f"evidence_refs[{index}] has invalid kind")
            refs.append(self.evidence_ref_verifier.validate(value, index))
        return refs

    def _validate_advancing_evidence(
        self,
        stage_id: str,
        outputs: Mapping[str, Any],
        refs: list[dict[str, Any]],
    ) -> None:
        if stage_id not in _EVIDENCE_SENSITIVE_STAGES:
            return super()._validate_advancing_evidence(stage_id, outputs, refs)
        resolved = [
            ref for ref in refs if self.evidence_ref_verifier.is_resolved(ref)
        ]
        if not resolved:
            raise ValueError(
                f"ADVANCE for {stage_id} requires immutable hashed evidence_refs "
                "that resolve to repository bytes or commits"
            )
        return super()._validate_advancing_evidence(stage_id, outputs, resolved)

    def _require_ref_identity(
        self,
        refs: list[dict[str, Any]],
        identity: str,
        kinds: set[str],
        label: str,
    ) -> None:
        if not any(
            ref["kind"] in kinds
            and self.evidence_ref_verifier.identity(ref) == identity
            for ref in refs
        ):
            raise ValueError(f"{label} evidence ref does not bind identity {identity}")

    @staticmethod
    def _ordered_record(record: Mapping[str, Any]) -> dict[str, Any]:
        ordered = {
            "schema_version": record["schema_version"],
            "record_id": record["record_id"],
        }
        if "handoff_id" in record:
            ordered["handoff_id"] = record["handoff_id"]
        for field in (
            "invocation_id",
            "stage_id",
            "role_id",
            "authority",
        ):
            ordered[field] = record[field]
        if "invocation_snapshot" in record:
            ordered["invocation_snapshot"] = record["invocation_snapshot"]
        for field in (
            "task_lineage",
            "status",
            "disposition",
            "outputs",
            "evidence_refs",
        ):
            ordered[field] = record[field]
        if "route_key" in record:
            ordered["route_key"] = record["route_key"]
        if "blocking_reason" in record:
            ordered["blocking_reason"] = record["blocking_reason"]
        ordered["transition"] = record["transition"]
        ordered["validation"] = record["validation"]
        return ordered

    def _require_outcome_snapshot(self, commit: str) -> None:
        super()._require_outcome_snapshot(commit)
        for relative in (
            ".terminus/execution/evidence_refs.py",
            ".terminus/execution/executor.py",
            ".terminus/execution/handoff_contract.py",
            ".terminus/execution/record_core.py",
            ".terminus/execution/record.py",
        ):
            current = (self.root / relative).read_bytes()
            committed = subprocess.run(
                ["git", "-C", str(self.root), "show", f"{commit}:{relative}"],
                check=True,
                capture_output=True,
            ).stdout
            if current != committed:
                raise ValueError(
                    "control_plane_commit does not match loaded execution-record implementation: "
                    + relative
                )
