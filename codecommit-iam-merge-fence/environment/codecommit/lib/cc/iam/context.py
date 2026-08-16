from __future__ import annotations

from cc.iam.policy import repo_arn
from cc.models import AuthContext
from cc.util import full_ref


def build_context(
    principal: str,
    action: str,
    repo: str,
    reference: str,
    *,
    mfa: bool = False,
    source_ip: str = "127.0.0.1",
) -> AuthContext:
    return AuthContext(
        principal=principal,
        action=action,
        resource_arn=repo_arn(repo),
        reference=full_ref(reference),
        mfa=mfa,
        source_ip=source_ip,
    )
