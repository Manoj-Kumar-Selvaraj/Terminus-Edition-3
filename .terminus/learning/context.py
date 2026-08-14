"""Build reproducible agent learning/remediation context from registry chain heads."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Mapping

from feedback.model import content_hash
from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator
from remediation.planner import RemediationPlanner

from .projection import LearningProjector

_ACTIVE_REPAIR_STATES = frozenset({"OPEN", "ASSIGNED", "FEEDBACK_CONFLICT"})


class LearningContextBuilder:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.projector = LearningProjector(self.root, store=self.store)

    def build(
        self,
        *,
        stage_id: str,
        role_id: str,
        task_id: str | None,
        task_commit: str | None,
        domain: str | None = None,
        registry_heads: Mapping[str, str] | None = None,
        lesson_limit: int = 12,
    ) -> dict[str, Any]:
        heads = dict(registry_heads or self.store.heads())
        expected_keys = {"feedback", "findings", "lessons", "patterns", "remediations"}
        if set(heads) != expected_keys:
            raise ValueError("learning registry_heads are incomplete")
        lessons = self.projector.project(
            stage_id=stage_id,
            role_id=role_id,
            domain=domain,
            limit=lesson_limit,
            chain_head=heads["lessons"],
        )
        remediation_context = self._remediations(
            stage_id=stage_id,
            task_id=task_id,
            task_commit=task_commit,
            finding_head=heads["findings"],
            remediation_head=heads["remediations"],
        )
        context: dict[str, Any] = {
            "mode": "GENERALIZED_LESSONS_PLUS_OWNED_REMEDIATIONS",
            "registry_heads": heads,
            "lessons": lessons["lessons"],
            "remediations": remediation_context,
            "raw_feedback_exposed": False,
            "raw_historical_findings_exposed": False,
        }
        context["context_hash"] = content_hash(context)
        return context

    def validate_projection(
        self,
        packet_learning: Mapping[str, Any],
        *,
        stage_id: str,
        role_id: str,
        task_id: str | None,
        task_commit: str | None,
        domain: str | None = None,
    ) -> None:
        heads = packet_learning.get("registry_heads")
        if not isinstance(heads, Mapping):
            raise ValueError("learning context registry_heads are missing")
        expected = self.build(
            stage_id=stage_id,
            role_id=role_id,
            task_id=task_id,
            task_commit=task_commit,
            domain=domain,
            registry_heads={str(k): str(v) for k, v in heads.items()},
        )
        if dict(packet_learning) != expected:
            raise ValueError("invocation learning context does not match bound registries")

    def _remediations(
        self,
        *,
        stage_id: str,
        task_id: str | None,
        task_commit: str | None,
        finding_head: str,
        remediation_head: str,
    ) -> list[dict[str, Any]]:
        if not task_id or not task_commit:
            return []
        findings = {
            finding["finding_id"]: finding
            for finding in self.store.findings.latest_by(
                "finding_id", chain_head=finding_head
            )
        }
        selected: list[dict[str, Any]] = []
        for packet in self.store.remediations.latest_by(
            "remediation_id", chain_head=remediation_head
        ):
            self.schemas.validate("remediation", packet)
            finding = findings.get(packet["finding_id"])
            if not finding or finding.get("state") not in _ACTIVE_REPAIR_STATES:
                continue
            if finding["task_id"] != task_id or packet["task_id"] != task_id:
                continue
            if not self._is_ancestor(packet["input_task_commit"], task_commit):
                continue
            context = RemediationPlanner.context_for_stage(packet, stage_id)
            if context is not None:
                selected.append(context)
        selected.sort(key=lambda item: (item["finding_id"], item["remediation_id"]))
        return selected

    def _is_ancestor(self, ancestor: str, descendant: str) -> bool:
        return (
            subprocess.run(
                ["git", "-C", str(self.root), "merge-base", "--is-ancestor", ancestor, descendant],
                capture_output=True,
            ).returncode
            == 0
        )
