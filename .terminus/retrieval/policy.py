"""Fail-closed authorization and freshness filtering for retrieval."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from review_contract import role_contract_hash as current_role_contract_hash

from .models import InvocationContext

ALL_STAGES = "ALL_AUTHORIZED_STAGES"
ALL_ROLES = "ALL_AUTHORIZED_ROLES"

_STAGE_OWNER_OVERRIDES = {
    "SYSTEM_ARCHITECTURE": "A2_SYSTEM_ARCHITECT",
    "ENVIRONMENT_BUILD": "A2_ENVIRONMENT_BUILDER",
}

_STAGE_ROLE_OVERRIDES = {
    "PRE_LLMAJ": frozenset(
        {
            "TASK_ARCHITECT",
            "VERIFIER_ENGINEER",
            "ORIGINALITY_AUTHENTICITY_REVIEWER",
            "DIFFICULTY_REVIEWER",
            "COMPLIANCE_AUDITOR",
            "INSTRUCTION_REVIEWER",
            "ENGINEERING_DOCUMENTATION_REVIEWER",
            "COMPREHENSIVE_REVIEWER",
            "ADJUDICATOR",
        }
    )
}

_REVIEW_ROLE_LABELS = {
    "Q4_SPEC_TEST_CONTRACT_REVIEWER": "Spec-Test Contract Reviewer",
    "Q6_PRODUCTION_LOGIC_AUDITOR": "Production Logic Auditor",
    "Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR": "Model Perspective Difficulty Simulator",
    "TASK_ARCHITECT": "Task Architect",
    "VERIFIER_ENGINEER": "Verifier Engineer",
    "ORIGINALITY_AUTHENTICITY_REVIEWER": "Originality & Authenticity Reviewer",
    "DIFFICULTY_REVIEWER": "Difficulty Reviewer",
    "COMPLIANCE_AUDITOR": "Compliance Auditor",
    "INSTRUCTION_REVIEWER": "Instruction Reviewer",
    "ENGINEERING_DOCUMENTATION_REVIEWER": "Engineering Documentation Reviewer",
    "HUMAN_QUALITY_REVIEWER": "Human Quality Reviewer",
    "COMPREHENSIVE_REVIEWER": "Comprehensive Reviewer",
    "TRAJECTORY_ANALYST": "Trajectory Analyst",
    "ADJUDICATOR": "Adjudicator",
}


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


class RetrievalPolicy:
    """Load stage, visibility, and metadata contracts and authorize chunks."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        agents = self.root / ".terminus" / "agents"
        self.stage_registry = self._load(agents / "stage_contracts.json")
        self.visibility_registry = self._load(agents / "evidence_visibility.json")
        self.metadata_registry = self._load(agents / "retrieval_metadata.json")

        self.stages = {
            item["id"]: item for item in self.stage_registry.get("stages", [])
        }
        self.visibility = {
            item["stage_id"]: item
            for item in self.visibility_registry.get("stages", [])
        }
        self.source_profiles = self.metadata_registry.get("source_profiles", {})
        self.source_kinds = frozenset(self.metadata_registry.get("source_kinds", []))
        self.evidence_classes = frozenset(
            self.visibility_registry.get("evidence_classes", {})
        )
        self.role_ids = frozenset(
            self.metadata_registry.get("canonical_role_ids", [])
        )
        self.role_aliases = dict(self.metadata_registry.get("role_aliases", {}))

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"expected object in {path}")
        return value

    @staticmethod
    def _normalize_participant(value: str) -> str:
        return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")

    def canonical_role(self, role: str) -> str:
        canonical = self.role_aliases.get(role, role)
        if canonical not in self.role_ids:
            raise ValueError(f"unknown retrieval role id: {role}")
        return canonical

    def _canonical_stage_participant(self, label: str) -> str:
        direct = self.role_aliases.get(label)
        if direct in self.role_ids:
            return str(direct)
        if label in self.role_ids:
            return label

        target = self._normalize_participant(label)
        matches: set[str] = set()
        for alias, role_id in self.role_aliases.items():
            alias_key = self._normalize_participant(alias)
            if (
                alias_key == target
                or alias_key.endswith(f"_{target}")
                or target.endswith(f"_{alias_key}")
            ):
                matches.add(role_id)
        for role_id in self.role_ids:
            role_key = self._normalize_participant(role_id)
            if role_key == target or role_key.endswith(f"_{target}"):
                matches.add(role_id)
        if len(matches) != 1:
            raise ValueError(
                f"stage participant {label!r} does not resolve uniquely to a canonical role"
            )
        return next(iter(matches))

    def allowed_roles_for_stage(self, stage_id: str) -> frozenset[str]:
        stage = self.stages.get(stage_id)
        if stage is None:
            raise ValueError(f"unknown retrieval stage id: {stage_id}")

        roles: set[str] = {"CI_ORCHESTRATOR"}
        if stage.get("lifecycle") == "creation":
            roles.add("CREATION_CONTROLLER")

        owner_override = _STAGE_OWNER_OVERRIDES.get(stage_id)
        if owner_override:
            roles.add(owner_override)
        else:
            owner = stage.get("owner")
            if not isinstance(owner, str) or not owner.strip():
                raise ValueError(f"stage {stage_id} has no canonical owner")
            roles.add(self._canonical_stage_participant(owner))

        explicit_roles = _STAGE_ROLE_OVERRIDES.get(stage_id)
        if explicit_roles is not None:
            roles.update(explicit_roles)
        else:
            reviewers = stage.get("semantic_reviewers", [])
            if not isinstance(reviewers, list):
                raise ValueError(f"stage {stage_id} semantic_reviewers must be a list")
            for reviewer in reviewers:
                if not isinstance(reviewer, str) or not reviewer.strip():
                    raise ValueError(f"stage {stage_id} has invalid semantic reviewer")
                roles.add(self._canonical_stage_participant(reviewer))
        return frozenset(roles)

    def validate_context(self, context: InvocationContext) -> InvocationContext:
        if context.stage_id not in self.stages:
            raise ValueError(f"unknown retrieval stage id: {context.stage_id}")
        canonical = self.canonical_role(context.role_id)
        allowed_roles = self.allowed_roles_for_stage(context.stage_id)
        if canonical not in allowed_roles:
            raise ValueError(
                f"retrieval role {canonical} is not authorized for stage {context.stage_id}"
            )
        if canonical == context.role_id:
            return context
        return InvocationContext(
            stage_id=context.stage_id,
            role_id=canonical,
            task_id=context.task_id,
            task_commit=context.task_commit,
            control_plane_commit=context.control_plane_commit,
            role_contract_hash=context.role_contract_hash,
            packet_binding=context.packet_binding,
            review_scope_hash=context.review_scope_hash,
            ci_run_id=context.ci_run_id,
            policy_versions=context.policy_versions,
            allowed_evidence_classes=context.allowed_evidence_classes,
            excluded_evidence_classes=context.excluded_evidence_classes,
            allowed_sensitivities=context.allowed_sensitivities,
        )

    def retrieval_mode(self, stage_id: str) -> str:
        try:
            return str(self.visibility[stage_id]["retrieval_mode"])
        except KeyError as exc:
            raise ValueError(f"missing visibility contract for {stage_id}") from exc

    def mandatory_exact_paths(self, stage_id: str) -> tuple[str, ...]:
        stage = self.stages.get(stage_id)
        if stage is None:
            raise ValueError(f"unknown retrieval stage id: {stage_id}")
        values = [*stage.get("policy_files", []), *stage.get("prompt_files", [])]
        return tuple(dict.fromkeys(str(value) for value in values))

    def authorized_evidence_classes(
        self, context: InvocationContext
    ) -> frozenset[str]:
        context = self.validate_context(context)
        contract = self.visibility[context.stage_id]
        stage_allowed = set(contract.get("required_evidence_classes", []))
        stage_allowed.update(contract.get("allowed_optional_evidence_classes", []))
        stage_allowed.difference_update(contract.get("excluded_evidence_classes", []))
        if context.allowed_evidence_classes is not None:
            stage_allowed.intersection_update(context.allowed_evidence_classes)
        stage_allowed.difference_update(context.excluded_evidence_classes)
        unknown = stage_allowed - self.evidence_classes
        if unknown:
            raise ValueError(f"unknown evidence classes in invocation: {sorted(unknown)}")
        return frozenset(stage_allowed)

    def authorize_chunk(
        self, metadata: Mapping[str, Any], context: InvocationContext
    ) -> AuthorizationDecision:
        try:
            context = self.validate_context(context)
        except ValueError as exc:
            return AuthorizationDecision(False, str(exc))

        source_kind = metadata.get("source_kind")
        profile = self.source_profiles.get(source_kind)
        if not isinstance(profile, dict):
            return AuthorizationDecision(False, "unknown source kind")

        evidence_class = metadata.get("evidence_class")
        if evidence_class != profile.get("default_evidence_class"):
            return AuthorizationDecision(False, "source/evidence profile mismatch")
        if metadata.get("sensitivity") != profile.get("default_sensitivity"):
            return AuthorizationDecision(False, "source/sensitivity profile mismatch")
        if metadata.get("solver_visible") is not profile.get("default_solver_visible"):
            return AuthorizationDecision(False, "source/solver-visible profile mismatch")

        if source_kind == "REVIEW_RESULT" and context.role_id != "CI_ORCHESTRATOR":
            role_label = _REVIEW_ROLE_LABELS.get(context.role_id)
            if role_label is None:
                return AuthorizationDecision(False, "review result consumer is not a reviewer role")
            expected_hash = current_role_contract_hash(self.root, role_label)
            if context.role_contract_hash != expected_hash:
                return AuthorizationDecision(False, "review result consumer role-contract hash mismatch")
            if metadata.get("role_contract_hash") != expected_hash:
                return AuthorizationDecision(False, "cold-review result producer mismatch")

        allowed = self.authorized_evidence_classes(context)
        if evidence_class not in allowed:
            return AuthorizationDecision(False, "evidence class not authorized")

        mode = self.retrieval_mode(context.stage_id)
        if mode == "SOLVER_VISIBLE_ONLY" and metadata.get("solver_visible") is not True:
            return AuthorizationDecision(False, "solver-visible-only stage")

        if context.allowed_sensitivities is not None:
            if metadata.get("sensitivity") not in context.allowed_sensitivities:
                return AuthorizationDecision(False, "sensitivity not authorized")

        stages = set(metadata.get("stage_applicability", []))
        if context.stage_id not in stages and ALL_STAGES not in stages:
            return AuthorizationDecision(False, "stage applicability mismatch")

        roles = set(metadata.get("role_applicability", []))
        if context.role_id not in roles and ALL_ROLES not in roles:
            return AuthorizationDecision(False, "role applicability mismatch")

        if profile.get("task_scoped"):
            if not context.task_id or not context.task_commit:
                return AuthorizationDecision(False, "task-scoped retrieval missing invocation binding")
            if metadata.get("task_id") != context.task_id:
                return AuthorizationDecision(False, "task id mismatch")

        freshness = set(metadata.get("freshness_scope", []))
        binding_checks = {
            "TASK_COMMIT": ("task_commit", context.task_commit),
            "CONTROL_PLANE_COMMIT": ("control_plane_commit", context.control_plane_commit),
            "ROLE_CONTRACT_HASH": ("role_contract_hash", context.role_contract_hash),
            "PACKET_BINDING": ("packet_binding", context.packet_binding),
            "REVIEW_SCOPE_HASH": ("review_scope_hash", context.review_scope_hash),
            "CI_RUN_ID": ("ci_run_id", context.ci_run_id),
        }
        for scope, (field, current) in binding_checks.items():
            if scope not in freshness:
                continue
            if current is None:
                return AuthorizationDecision(False, f"missing invocation {field}")
            if str(metadata.get(field)) != str(current):
                return AuthorizationDecision(False, f"stale {field}")

        if "POLICY_VERSION" in freshness:
            chunk_versions = metadata.get("policy_versions")
            if not isinstance(chunk_versions, dict) or not chunk_versions:
                return AuthorizationDecision(False, "missing chunk policy versions")
            for name, value in chunk_versions.items():
                if context.policy_versions.get(name) != value:
                    return AuthorizationDecision(False, f"stale policy version {name}")

        return AuthorizationDecision(True, "authorized")
