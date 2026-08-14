"""Compile one bounded executable handoff from the registered stage contracts."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

from learning.context import LearningContextBuilder
from retrieval.engine import RetrievalEngine
from retrieval.models import InvocationContext, RetrievalQuery
from retrieval.policy import RetrievalPolicy
from retrieval.store import RetrievalStore

from .acceptance import StageAcceptancePredicates
from .authority import ExecutionAuthority

_SHA = re.compile(r"^[0-9a-f]{40,64}$")
_VALID_SENSITIVITIES = frozenset(
    {"PUBLIC", "SOLVER_VISIBLE", "CONTROL_PLANE", "PRIVATE", "RESTRICTED"}
)
_CONTRACT_SNAPSHOT_PATHS = (
    ".terminus/agents/stage_contracts.json",
    ".terminus/agents/evidence_visibility.json",
    ".terminus/agents/retrieval_metadata.json",
    ".terminus/agents/stage_acceptance_predicates.json",
    ".terminus/agents/schemas/stage_acceptance_predicates.schema.json",
    ".terminus/agents/schemas/feedback_event.schema.json",
    ".terminus/agents/schemas/finding.schema.json",
    ".terminus/agents/schemas/remediation_packet.schema.json",
    ".terminus/agents/schemas/lesson.schema.json",
    ".terminus/agents/schemas/pattern.schema.json",
    ".terminus/feedback/model.py",
    ".terminus/feedback/registry.py",
    ".terminus/feedback/schema_validation.py",
    ".terminus/feedback/provenance.py",
    ".terminus/feedback/closure.py",
    ".terminus/remediation/planner.py",
    ".terminus/remediation/progress.py",
    ".terminus/learning/context.py",
    ".terminus/learning/integrity.py",
    ".terminus/learning/projection.py",
    ".terminus/learning/knowledge/lessons.jsonl",
    ".terminus/learning/knowledge/patterns.jsonl",
    ".terminus/agents/STAGE_INVOCATION.md",
)
_POLICY_VERSION_SOURCES = {
    "agent_system": (".terminus/AGENT_SYSTEM.md", "Agent-system policy version"),
    "specialist_prompt": (".terminus/agents/PROMPTS.md", "Prompt policy version"),
    "specialist_protocol": (".terminus/agents/PROTOCOL.md", "Policy version"),
    "pre_llmaj_panel": (".terminus/reviewers/PRE_LLMAJ.md", "Panel policy version"),
    "comprehensive_reviewer": (
        ".terminus/agents/COMPREHENSIVE_REVIEWER.md",
        "Reviewer policy version",
    ),
}


class StageInvocationBuilder:
    """Project stage/role authority, learning and declared inputs into one bounded packet."""

    schema_version = "1.0"

    def __init__(self, root: Path, policy: RetrievalPolicy | None = None):
        self.root = root.resolve()
        self.policy = policy or RetrievalPolicy(self.root)
        self.execution_authority = ExecutionAuthority(self.policy)
        self.acceptance = StageAcceptancePredicates(self.root)
        self.learning = LearningContextBuilder(self.root)

    def build(
        self,
        context: InvocationContext,
        available_inputs: Mapping[str, Any],
        *,
        retrieval_query: str | None = None,
        retrieval_db: Path | None = None,
        retrieval_limit: int = 10,
        max_chars: int = 30000,
    ) -> dict[str, Any]:
        """Return a deterministic READY or BLOCKED_MISSING_INPUTS invocation packet."""
        context = self._validate_authority(context)
        stage = self.policy.stages[context.stage_id]
        input_contract = stage.get("input_contract", {})
        output_contract = stage.get("output_contract", {})

        required_names = tuple(str(value) for value in input_contract.get("required_fields", []))
        optional_names = tuple(str(value) for value in input_contract.get("optional_fields", []))
        declared = set(required_names) | set(optional_names)

        supplied = dict(available_inputs)
        self._validate_json_inputs(supplied)
        required_inputs = {name: supplied[name] for name in required_names if name in supplied}
        optional_inputs = {name: supplied[name] for name in optional_names if name in supplied}
        missing = [name for name in required_names if name not in supplied]
        ignored_count = len(set(supplied) - declared)
        readiness = "BLOCKED_MISSING_INPUTS" if missing else "READY"

        authorized = sorted(self.policy.authorized_evidence_classes(context))
        excluded = sorted(self.policy.evidence_classes - set(authorized))
        mandatory_exact_reads = list(self.policy.mandatory_exact_paths(context.stage_id))
        self._require_paths_at_commit(
            context.control_plane_commit,
            mandatory_exact_reads,
            "mandatory exact read",
        )

        retrieval = self._retrieval_projection(
            context,
            query=retrieval_query,
            db_path=retrieval_db,
            limit=retrieval_limit,
            max_chars=max_chars,
            executable=readiness == "READY",
        )
        learning = self.learning.build(
            stage_id=context.stage_id,
            role_id=context.role_id,
            task_id=context.task_id,
            task_commit=context.task_commit,
        )
        packet: dict[str, Any] = {
            "schema_version": self.schema_version,
            "readiness": readiness,
            "authority": {
                "task_id": context.task_id,
                "task_commit": context.task_commit,
                "control_plane_commit": context.control_plane_commit,
            },
            "stage": {
                "stage_id": context.stage_id,
                "role_id": context.role_id,
                "owner": stage["owner"],
                "role_class": stage["role_class"],
            },
            "policy": {
                "versions": self._policy_versions(),
                "control_plane_snapshot": self._contract_snapshot(
                    context.control_plane_commit
                ),
                "mandatory_exact_reads": mandatory_exact_reads,
            },
            "input_contract": {
                "required_fields": list(required_names),
                "optional_fields": list(optional_names),
                "required_inputs": required_inputs,
                "optional_inputs": optional_inputs,
                "missing_required_fields": missing,
                "ignored_undeclared_input_count": ignored_count,
            },
            "output_contract": {
                "allowed_status_values": list(output_contract.get("status_values", [])),
                "required_fields": list(output_contract.get("required_fields", [])),
                "optional_fields": list(output_contract.get("optional_fields", [])),
                "persisted_artifacts": list(output_contract.get("persisted_artifacts", [])),
            },
            "evidence": {
                "authorized_classes": authorized,
                "excluded_classes": excluded,
            },
            "retrieval": retrieval,
            "learning": learning,
        }
        packet["invocation_id"] = self._invocation_id(packet)
        return packet

    @staticmethod
    def _invocation_id(packet: Mapping[str, Any]) -> str:
        canonical = json.dumps(
            packet,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return "inv_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _validate_authority(self, context: InvocationContext) -> InvocationContext:
        if context.stage_id not in self.policy.stages:
            raise ValueError(f"unknown stage_id: {context.stage_id}")
        expected_role = self.execution_authority.primary_role_for_stage(context.stage_id)
        if context.role_id != expected_role:
            raise ValueError(
                f"role_id {context.role_id} is not the primary authority for {context.stage_id}; expected {expected_role}"
            )
        self._require_git_commit(context.task_commit, "task_commit")
        self._require_git_commit(context.control_plane_commit, "control_plane_commit")
        return context

    def _retrieval_projection(
        self,
        context: InvocationContext,
        *,
        query: str | None,
        db_path: Path | None,
        limit: int,
        max_chars: int,
        executable: bool,
    ) -> dict[str, Any]:
        if not executable or not query:
            return {
                "mode": "DECLARED_EXACT_READS_ONLY",
                "documents": [],
                "document_count": 0,
                "query": query or "",
            }
        if db_path is None:
            db_path = self.root / ".terminus" / "retrieval" / "retrieval.db"
        store = RetrievalStore(db_path)
        try:
            engine = RetrievalEngine(self.root, store, self.policy)
            result = engine.query(
                RetrievalQuery(
                    context=context,
                    query=query,
                    limit=limit,
                    max_chars=max_chars,
                )
            )
        finally:
            store.close()
        return result

    def _policy_versions(self) -> dict[str, str]:
        versions: dict[str, str] = {}
        for key, (relative, marker) in _POLICY_VERSION_SOURCES.items():
            text = (self.root / relative).read_text(encoding="utf-8")
            match = re.search(rf"{re.escape(marker)}:\s*`([^`]+)`", text)
            if not match:
                raise ValueError(f"cannot resolve {key} policy version from {relative}")
            versions[key] = match.group(1)
        return versions

    def _contract_snapshot(self, commit: str) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        for relative in _CONTRACT_SNAPSHOT_PATHS:
            raw = subprocess.run(
                ["git", "-C", str(self.root), "show", f"{commit}:{relative}"],
                check=True,
                capture_output=True,
            ).stdout
            snapshot[relative] = "sha256:" + hashlib.sha256(raw).hexdigest()
        return snapshot

    def _require_paths_at_commit(
        self, commit: str, paths: list[str], label: str
    ) -> None:
        for relative in paths:
            result = subprocess.run(
                ["git", "-C", str(self.root), "cat-file", "-e", f"{commit}:{relative}"],
                capture_output=True,
            )
            if result.returncode != 0:
                raise ValueError(f"{label} path is unavailable at control plane commit: {relative}")

    def _require_git_commit(self, commit: str, label: str) -> None:
        if not isinstance(commit, str) or not _SHA.fullmatch(commit):
            raise ValueError(f"{label} must be a full Git commit")
        result = subprocess.run(
            ["git", "-C", str(self.root), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(f"{label} is unavailable in repository history")

    def _validate_json_inputs(self, value: Mapping[str, Any]) -> None:
        try:
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("stage invocation inputs must be JSON-compatible") from exc
