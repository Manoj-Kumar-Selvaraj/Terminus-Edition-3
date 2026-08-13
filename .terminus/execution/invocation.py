"""Compile one bounded executable handoff from the registered stage contracts."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

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
    """Project stage/role authority and declared inputs into one bounded packet."""

    schema_version = "1.0"

    def __init__(self, root: Path, policy: RetrievalPolicy | None = None):
        self.root = root.resolve()
        self.policy = policy or RetrievalPolicy(self.root)
        self.execution_authority = ExecutionAuthority(self.policy)
        self.acceptance = StageAcceptancePredicates(self.root)

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

        authority: dict[str, Any] = {
            "control_plane_commit": context.control_plane_commit,
            "policy_versions": dict(sorted(context.policy_versions.items())),
        }
        optional_authority = {
            "task_id": context.task_id,
            "task_commit": context.task_commit,
            "role_contract_hash": context.role_contract_hash,
            "packet_binding": context.packet_binding,
            "review_scope_hash": context.review_scope_hash,
            "ci_run_id": context.ci_run_id,
        }
        authority.update({key: value for key, value in optional_authority.items() if value is not None})

        status_values = [str(value) for value in output_contract.get("status_values", [])]
        acceptance_predicates = {
            status: self.acceptance.predicates_for(context.stage_id, status)
            for status in status_values
            if self.acceptance.predicates_for(context.stage_id, status)
        }

        packet: dict[str, Any] = {
            "schema_version": self.schema_version,
            "readiness": readiness,
            "stage": {
                "stage_id": context.stage_id,
                "role_id": context.role_id,
                "owner": str(stage.get("owner", "")),
                "role_class": str(stage.get("role_class", "")),
                "lifecycle": str(stage.get("lifecycle", "")),
            },
            "authority": authority,
            "inputs": {"required": required_inputs, "optional": optional_inputs},
            "missing_required_inputs": missing,
            "ignored_input_count": ignored_count,
            "evidence": {
                "retrieval_mode": self.policy.retrieval_mode(context.stage_id),
                "mandatory_exact_reads": mandatory_exact_reads,
                "authorized_evidence_classes": authorized,
                "excluded_evidence_classes": excluded,
                "evidence_required": [str(value) for value in stage.get("evidence_required", [])],
            },
            "retrieval": retrieval,
            "output_contract": {
                "allowed_status_values": status_values,
                "required_fields": [str(value) for value in output_contract.get("required_fields", [])],
                "optional_fields": [str(value) for value in output_contract.get("optional_fields", [])],
                "persisted_artifacts": [str(value) for value in output_contract.get("persisted_artifacts", [])],
                "deterministic_validators": [str(value) for value in stage.get("deterministic_validators", [])],
                "semantic_reviewers": [str(value) for value in stage.get("semantic_reviewers", [])],
            },
            "acceptance_predicates": acceptance_predicates,
            "routing": {
                "failure_routes": {str(key): str(value) for key, value in stage.get("failure_routes", {}).items()},
                "success_transition": str(stage.get("success_transition", "")),
                "stale_on": [str(value) for value in stage.get("stale_on", [])],
            },
        }
        packet["invocation_id"] = self._invocation_id(packet)
        return self._ordered_packet(packet)

    def _validate_authority(self, context: InvocationContext) -> InvocationContext:
        context = self.execution_authority.validate_context(context)
        if not context.control_plane_commit or not _SHA.fullmatch(context.control_plane_commit):
            raise ValueError("stage invocation requires an exact control_plane_commit")
        self._require_git_commit(context.control_plane_commit, "control_plane_commit")
        self._require_loaded_contract_snapshot(context.control_plane_commit)

        if bool(context.task_id) != bool(context.task_commit):
            raise ValueError("task_id and task_commit must be supplied together")
        if context.task_commit:
            if not _SHA.fullmatch(context.task_commit):
                raise ValueError("task_commit must be a full hexadecimal Git commit")
            self._require_git_commit(context.task_commit, "task_commit")

        allowed = context.allowed_evidence_classes
        if allowed is not None:
            unknown = set(allowed) - self.policy.evidence_classes
            if unknown:
                raise ValueError(f"unknown allowed evidence classes: {sorted(unknown)}")
        unknown_excluded = set(context.excluded_evidence_classes) - self.policy.evidence_classes
        if unknown_excluded:
            raise ValueError(f"unknown excluded evidence classes: {sorted(unknown_excluded)}")
        if context.allowed_sensitivities is not None:
            unknown_sensitivity = set(context.allowed_sensitivities) - _VALID_SENSITIVITIES
            if unknown_sensitivity:
                raise ValueError(f"unknown allowed sensitivities: {sorted(unknown_sensitivity)}")
        self._validate_policy_versions(context)
        return context

    def _require_loaded_contract_snapshot(self, commit: str) -> None:
        """Refuse to label current in-memory contracts as a different Git snapshot."""
        for relative in _CONTRACT_SNAPSHOT_PATHS:
            current = (self.root / relative).read_bytes()
            committed = self._git_bytes("show", f"{commit}:{relative}")
            if current != committed:
                raise ValueError(
                    "control_plane_commit does not match the loaded stage-invocation contracts: "
                    f"{relative}"
                )

    def _validate_policy_versions(self, context: InvocationContext) -> None:
        for key, supplied in context.policy_versions.items():
            source = _POLICY_VERSION_SOURCES.get(key)
            if source is None:
                continue
            path, label = source
            text = self._git_text("show", f"{context.control_plane_commit}:{path}")
            match = re.search(
                rf"^{re.escape(label)}:\s*`([^`]+)`\s*$",
                text,
                flags=re.MULTILINE,
            )
            if not match:
                raise ValueError(f"cannot resolve {key} policy version at control_plane_commit")
            actual = match.group(1).strip()
            if str(supplied) != actual:
                raise ValueError(f"stale policy version {key}: supplied {supplied}, current {actual}")

    def _require_paths_at_commit(self, commit: str, paths: list[str], label: str) -> None:
        for path in paths:
            result = subprocess.run(
                ["git", "-C", str(self.root), "cat-file", "-e", f"{commit}:{path}"],
                capture_output=True,
            )
            if result.returncode != 0:
                raise ValueError(f"{label} missing at control_plane_commit: {path}")

    def _require_git_commit(self, commit: str, label: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(f"{label} is not available in repository history: {commit}")

    def _git_text(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def _git_bytes(self, *args: str) -> bytes:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
        ).stdout

    @staticmethod
    def _validate_json_inputs(values: Mapping[str, Any]) -> None:
        for key in values:
            if not isinstance(key, str) or not key:
                raise ValueError("stage invocation input names must be non-empty strings")
        try:
            json.dumps(values, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise ValueError("stage invocation inputs must be JSON-compatible") from exc

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
        normalized_query = query.strip() if query and query.strip() else None
        if normalized_query is None:
            return {"status": "NOT_REQUESTED", "query": None, "retrieved_context": [], "retrieved_chars": 0}
        if not executable:
            return {"status": "SKIPPED_BLOCKED_INPUTS", "query": normalized_query, "retrieved_context": [], "retrieved_chars": 0}
        if limit <= 0:
            raise ValueError("retrieval_limit must be positive")
        if max_chars < 0:
            raise ValueError("max_chars must be non-negative")
        path = db_path.resolve() if db_path is not None else self.root / ".terminus" / "cache" / "retrieval.sqlite3"
        if not path.is_file():
            return {"status": "DIRECT_READ_FALLBACK", "query": normalized_query, "retrieved_context": [], "retrieved_chars": 0}
        with RetrievalStore(path) as store:
            engine = RetrievalEngine(self.root, store, policy=self.policy)
            bundle = engine.context_bundle(
                context,
                RetrievalQuery(text=normalized_query, limit=limit),
                max_chars=max_chars,
            )
        return {
            "status": "INDEXED_CONTEXT",
            "query": normalized_query,
            "retrieved_context": bundle["retrieved_context"],
            "retrieved_chars": int(bundle["retrieved_chars"]),
        }

    @staticmethod
    def _invocation_id(packet: Mapping[str, Any]) -> str:
        """Bind to authoritative content/provenance, not diagnostic rank score magnitudes."""
        identity = json.loads(json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        for item in identity.get("retrieval", {}).get("retrieved_context", []):
            if isinstance(item, dict):
                item.pop("score", None)
        payload = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return "inv_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _ordered_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": packet["schema_version"],
            "invocation_id": packet["invocation_id"],
            "readiness": packet["readiness"],
            "stage": packet["stage"],
            "authority": packet["authority"],
            "inputs": packet["inputs"],
            "missing_required_inputs": packet["missing_required_inputs"],
            "ignored_input_count": packet["ignored_input_count"],
            "evidence": packet["evidence"],
            "retrieval": packet["retrieval"],
            "output_contract": packet["output_contract"],
            "acceptance_predicates": packet["acceptance_predicates"],
            "routing": packet["routing"],
        }
