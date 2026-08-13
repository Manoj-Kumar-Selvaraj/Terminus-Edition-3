"""Canonical execution-role authority derived from stage contracts.

Retrieval audiences are intentionally broader because controllers must be able to
inspect/rout a stage without becoming that stage's executor. This module keeps
that observation permission separate from executable role authority.
"""

from __future__ import annotations

from retrieval.models import InvocationContext
from retrieval.policy import RetrievalPolicy

_OWNER_OVERRIDES = {
    "SYSTEM_ARCHITECTURE": "A2_SYSTEM_ARCHITECT",
    "ENVIRONMENT_BUILD": "A2_ENVIRONMENT_BUILDER",
}


class ExecutionAuthority:
    """Resolve roles that may actually execute one registered stage."""

    def __init__(self, policy: RetrievalPolicy):
        self.policy = policy

    def primary_role_for_stage(self, stage_id: str) -> str:
        stage = self.policy.stages.get(stage_id)
        if stage is None:
            raise ValueError(f"unknown execution stage id: {stage_id}")
        override = _OWNER_OVERRIDES.get(stage_id)
        if override is not None:
            return override
        owner = stage.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError(f"stage {stage_id} has no canonical execution owner")
        return self.policy._canonical_stage_participant(owner)

    def roles_for_stage(self, stage_id: str) -> frozenset[str]:
        """Return owner + declared semantic executors/reviewers, excluding observers."""
        stage = self.policy.stages.get(stage_id)
        if stage is None:
            raise ValueError(f"unknown execution stage id: {stage_id}")

        retrieval_roles = set(self.policy.allowed_roles_for_stage(stage_id))
        primary = self.primary_role_for_stage(stage_id)
        roles: set[str] = {primary}

        # Declared semantic reviewers are legitimate role-specific executions under
        # this stage. PRE_LLMAJ uses a grouped label in the registry, so the
        # retrieval policy has already expanded it into concrete canonical roles;
        # keep all non-observer roles from that expansion.
        reviewers = stage.get("semantic_reviewers", [])
        if not isinstance(reviewers, list):
            raise ValueError(f"stage {stage_id} semantic_reviewers must be a list")
        grouped_reviewer = any(
            isinstance(value, str) and value.strip() == "Stage-B specialists"
            for value in reviewers
        )
        if grouped_reviewer:
            roles.update(
                retrieval_roles
                - {"CI_ORCHESTRATOR", "CREATION_CONTROLLER"}
            )
        else:
            for reviewer in reviewers:
                if not isinstance(reviewer, str) or not reviewer.strip():
                    raise ValueError(f"stage {stage_id} has invalid semantic reviewer")
                roles.add(self.policy._canonical_stage_participant(reviewer))

        # A controller is executable only when it is the actual stage owner or is
        # explicitly named as a semantic reviewer; generic routing/observation
        # access from RetrievalPolicy is never inherited as execution authority.
        unknown = roles - self.policy.role_ids
        if unknown:
            raise ValueError(
                f"stage {stage_id} execution roles are not canonical: {sorted(unknown)}"
            )
        if not roles.issubset(retrieval_roles):
            raise ValueError(
                f"stage {stage_id} execution authority exceeds retrieval authority"
            )
        return frozenset(roles)

    def validate_context(self, context: InvocationContext) -> InvocationContext:
        canonical = self.policy.canonical_role(context.role_id)
        roles = self.roles_for_stage(context.stage_id)
        if canonical not in roles:
            raise ValueError(
                f"execution role {canonical} is not authorized for stage {context.stage_id}"
            )
        # RetrievalPolicy performs the remaining canonicalization and verifies that
        # the execution role can also see this stage's retrieval envelope.
        return self.policy.validate_context(context)
