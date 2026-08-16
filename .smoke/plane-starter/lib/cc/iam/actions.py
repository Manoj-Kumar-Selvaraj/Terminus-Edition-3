"""Action registry and action-pattern matching."""

from __future__ import annotations

from cc.errors import ValidationException

GIT_PULL = "codecommit:GitPull"
GIT_PUSH = "codecommit:GitPush"
GET_REPOSITORY = "codecommit:GetRepository"
CREATE_PULL_REQUEST = "codecommit:CreatePullRequest"
UPDATE_APPROVAL_STATE = "codecommit:UpdatePullRequestApprovalState"
MERGE_BY_FAST_FORWARD = "codecommit:MergePullRequestByFastForward"
START_PIPELINE = "pipeline:StartPipelineExecution"
QUERY_AUTHZ_LOG = "audit:QueryAuthzLog"
DISPATCH_OUTBOX = "webhook:DispatchOutbox"
LIST_OUTBOX = "webhook:ListOutbox"

REGISTRY = {
    GIT_PULL: "read repository objects",
    GIT_PUSH: "update a repository ref",
    GET_REPOSITORY: "read repository metadata",
    CREATE_PULL_REQUEST: "open a pull request",
    UPDATE_APPROVAL_STATE: "stamp a pull request",
    MERGE_BY_FAST_FORWARD: "land a pull request by fast-forward",
    START_PIPELINE: "start a bound pipeline execution",
    QUERY_AUTHZ_LOG: "read recorded authorization decisions",
    DISPATCH_OUTBOX: "drain the webhook outbox",
    LIST_OUTBOX: "read the webhook outbox",
}

REF_SCOPED = frozenset({GIT_PUSH, GIT_PULL, MERGE_BY_FAST_FORWARD, START_PIPELINE})


def service_of(action: str) -> str:
    """Service prefix of a fully qualified action name."""
    return action.split(":", 1)[0] if ":" in action else ""


def verb_of(action: str) -> str:
    """Verb portion of a fully qualified action name."""
    return action.split(":", 1)[1] if ":" in action else action


def validate_action(action: str) -> str:
    """Reject action names the control plane does not implement."""
    if action not in REGISTRY:
        raise ValidationException("UNKNOWN_ACTION", f"unsupported action {action!r}")
    return action


def is_ref_scoped(action: str) -> bool:
    """True when a request for this action must carry codecommit:References."""
    return action in REF_SCOPED


def action_matches(pattern: str, requested: str) -> bool:
    """Test whether a policy Action entry covers the requested action."""
    if pattern == "*":
        return True
    left = verb_of(pattern).lower()
    right = verb_of(requested).lower()
    if left == right:
        return True
    return left[:3] == right[:3]


def any_action_matches(patterns: tuple[str, ...], requested: str) -> bool:
    """True when at least one Action entry of a statement covers the request."""
    return any(action_matches(pattern, requested) for pattern in patterns)


def wildcard_patterns(patterns: tuple[str, ...]) -> list[str]:
    """Action entries in a statement that are wildcards rather than exact names."""
    return [pattern for pattern in patterns if pattern == "*" or pattern.endswith(":*")]
