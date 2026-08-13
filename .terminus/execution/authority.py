"""Canonical execution-role authority derived from stage ownership.

Retrieval audiences are intentionally broader because controllers and reviewers may
need to inspect/rout a stage without becoming that stage's executor. Generic stage
invocation/record/state authority belongs only to the canonical stage owner.
Semantic reviewers remain independent evidence providers under their own
packet/role contracts; their results are inputs to the owning aggregate stage.
"""

from __future__ import annotations

from retrieval.models import InvocationContext
from retrieval.policy import RetrievalPolicy

_OWNER_OVERRIDES = {
    "SYSTEM_ARCHITECTURE": "A2_SYSTEM_ARCHITECT",
    "ENVIRONMENT_BUILD": "A2_ENVIRONMENT_BUILDER",
}


class ExecutionAuthority:
    """Resolve the single canonical executor of each registered aggregate stage."""

    def __init__(self, policy: RetrievalPolicy):
        self.policy = policy

    def primary_role_for_stage(self, stage_id: str) -> str:
        stage = self.policy.stages.get(stage_id)
        if stage is None:
            raise ValueError(f"unknown execution stage id: {stage_id}")
        override = _OWNER_OVERRIDES.get(stage_id)
        if override is not None:
            role = override
        else:
            owner = stage.get("owner")
            if not isinstance(owner, str) or not owner.strip():
                raise ValueError(f"stage {stage_id} has no canonical execution owner")
            role = self.policy._canonical_stage_participant(owner)
        if role not in self.policy.role_ids:
            raise ValueError(f"stage {stage_id} owner role is not canonical: {role}")
        if role not in self.policy.allowed_roles_for_stage(stage_id):
            raise ValueError(
                f"stage {stage_id} owner execution authority exceeds retrieval authority"
            )
        return role

    def roles_for_stage(self, stage_id: str) -> frozenset[str]:
        """Return exactly the aggregate stage owner role.

        `semantic_reviewers` are not alternative executors of the aggregate stage.
        They use their packet-bound or role-specific contracts and feed evidence to
        the owner, which alone emits the stage status/output consumed by the
        execution ledger.
        """
        return frozenset({self.primary_role_for_stage(stage_id)})

    def validate_context(self, context: InvocationContext) -> InvocationContext:
        canonical = self.policy.canonical_role(context.role_id)
        roles = self.roles_for_stage(context.stage_id)
        if canonical not in roles:
            raise ValueError(
                f"execution role {canonical} is not authorized for stage {context.stage_id}"
            )
        # RetrievalPolicy performs remaining canonicalization/evidence checks. The
        # execution role must be both the stage owner and a permitted retrieval role.
        return self.policy.validate_context(context)
