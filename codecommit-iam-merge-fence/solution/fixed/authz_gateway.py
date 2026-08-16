from __future__ import annotations

from typing import Any

from cc.audit.log import record
from cc.errors import AccessDenied
from cc.iam.eval import authorize
from cc.models import AuditEvent


def gated_authorize(
    principal: str,
    action: str,
    repo: str,
    reference: str,
    *,
    mfa: bool = False,
    source_ip: str = "127.0.0.1",
    fixed: bool = False,
) -> Any:
    fixed = True
    try:
        ctx = authorize(
            principal, action, repo, reference, mfa=mfa, source_ip=source_ip, fixed=fixed
        )
        record(
            AuditEvent(
                principal,
                action,
                ctx.resource_arn,
                ctx.reference,
                True,
                "allow",
                source_ip,
                mfa,
            ),
            fixed=fixed,
        )
        return ctx
    except AccessDenied as exc:
        from cc.iam.policy import repo_arn
        from cc.util import full_ref

        record(
            AuditEvent(
                principal,
                action,
                repo_arn(repo),
                full_ref(reference),
                False,
                exc.code or "deny",
                source_ip,
                mfa,
            ),
            fixed=fixed,
        )
        raise
