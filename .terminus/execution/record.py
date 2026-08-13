"""Canonical execution-record builder with fail-closed evidence resolution."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Mapping

from retrieval.policy import RetrievalPolicy

from . import record_core as _core
from .evidence_refs import EvidenceReferenceVerifier

_SHA = _core._SHA
_SHA256 = _core._SHA256
_EVIDENCE_KINDS = _core._EVIDENCE_KINDS
_TASK_MUTATING_ROLE_CLASSES = _core._TASK_MUTATING_ROLE_CLASSES
_EVIDENCE_SENSITIVE_STAGES = _core._EVIDENCE_SENSITIVE_STAGES


class ExecutionRecordBuilder(_core.ExecutionRecordBuilder):
    """Extend the core recorder with resolvable immutable evidence enforcement."""

    def __init__(self, root: Path, policy: RetrievalPolicy | None = None):
        super().__init__(root, policy)
        self.evidence_ref_verifier = EvidenceReferenceVerifier(self.root)

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

    def _require_outcome_snapshot(self, commit: str) -> None:
        super()._require_outcome_snapshot(commit)
        for relative in (
            ".terminus/execution/evidence_refs.py",
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
