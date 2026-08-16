from __future__ import annotations

from typing import Any

from cc.iam import actions as iam_actions
from cc.iam.eval import explain
from cc.services import authz_gateway

DEFAULT_ACTIONS = [iam_actions.GIT_PULL, iam_actions.GIT_PUSH, iam_actions.MERGE_FF]


def explain_matrix(
    principal: str,
    repo: str,
    refs: list[str],
    actions: list[str],
    *,
    mfa: bool = False,
    source_ip: str = "127.0.0.1",
    fixed: bool = False,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ref in refs:
        for action in actions:
            out.append(
                explain(
                    principal,
                    action,
                    repo,
                    ref,
                    mfa=mfa,
                    source_ip=source_ip,
                    fixed=fixed,
                )
            )
    return out


def try_authorize_many(requests: list[dict[str, Any]], *, fixed: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for req in requests:
        try:
            ctx = authz_gateway.gated_authorize(
                req["principal"],
                req["action"],
                req["repo"],
                req["reference"],
                mfa=bool(req.get("mfa")),
                source_ip=str(req.get("source_ip") or "127.0.0.1"),
                fixed=fixed,
            )
            results.append({"ok": True, "resource": ctx.resource_arn})
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "error": str(exc)})
    return results
