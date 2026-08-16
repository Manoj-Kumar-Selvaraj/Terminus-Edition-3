from __future__ import annotations

from typing import Any

from cc.iam_decision_trace import compact_trace, trace_authorize


def simulate(
    principal: str,
    action: str,
    repo: str,
    reference: str,
    *,
    mfa: bool = False,
    source_ip: str = "127.0.0.1",
    fixed: bool = False,
) -> dict[str, Any]:
    trace = trace_authorize(
        principal, action, repo, reference, mfa=mfa, source_ip=source_ip, fixed=fixed
    )
    return {
        "principal": principal,
        "action": action,
        "repo": repo,
        "reference": reference,
        "allowed": trace.get("allowed"),
        "trace": compact_trace(trace),
        "steps": trace.get("steps"),
    }
