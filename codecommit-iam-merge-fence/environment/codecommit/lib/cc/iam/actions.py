from __future__ import annotations

GIT_PULL = "codecommit:GitPull"
GIT_PUSH = "codecommit:GitPush"
MERGE_FF = "codecommit:MergePullRequestByFastForward"
ALL_ACTIONS = (GIT_PULL, GIT_PUSH, MERGE_FF)


def normalize_action(action: str) -> str:
    return action.strip()


def action_matches(statement_action: str, requested: str) -> bool:
    """Broken starter: GitPull/GitPush treated as interchangeable; * is unbounded."""
    sa = normalize_action(statement_action)
    req = normalize_action(requested)
    if sa in ("*", "codecommit:*"):
        return req.startswith("codecommit:")
    if sa == req:
        return True
    # Broken: any Git* verb matches any other Git* verb
    if "Git" in sa and "Git" in req:
        return True
    return False


def action_matches_fixed(statement_action: str, requested: str) -> bool:
    sa = normalize_action(statement_action)
    req = normalize_action(requested)
    if sa in ("*", "codecommit:*"):
        return req in ALL_ACTIONS
    return sa == req


def expand_star(statement_action: str) -> tuple[str, ...]:
    sa = normalize_action(statement_action)
    if sa in ("*", "codecommit:*"):
        return ALL_ACTIONS
    return (sa,)
