"""Resolve the effective Terminus control-plane commit independently of state-only commits."""

from __future__ import annotations

import subprocess
from pathlib import Path

_CONTROL_PLANE_EXACT = frozenset(
    {
        "TERMINUS_3_AI_INSTRUCTIONS.md",
        "terminus3.sh",
    }
)
_CONTROL_PLANE_PREFIXES = (
    ".github/workflows/terminus-",
    ".github/chat_inline_stage_",
    ".cursor/agents/terminus-",
    ".terminus/AGENT_SYSTEM.md",
    ".terminus/CONTINUE_SESSION.md",
    ".terminus/CURSOR_OPERATING.md",
    ".terminus/agents/",
    ".terminus/execution/",
    ".terminus/feedback/",
    ".terminus/learning/",
    ".terminus/remediation/",
    ".terminus/retrieval/",
    ".terminus/reviewers/",
    ".terminus/validate_",
    ".terminus/new_review_packet.py",
    ".terminus/review_contract.py",
    ".terminus/analyze_difficulty.py",
)


def is_control_plane_path(path: str) -> bool:
    """Return whether one repository path changes executable/policy control-plane semantics."""
    return path in _CONTROL_PLANE_EXACT or any(
        path.startswith(prefix) for prefix in _CONTROL_PLANE_PREFIXES
    )


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def resolve_control_plane_commit(root: Path, head: str = "HEAD") -> str:
    """Return the newest first-parent commit that materially changed the control plane.

    Durable lifecycle state, review results, sessions, task packages and generated execution
    records may advance repository HEAD without changing the policy/executor identity to which
    StageInvocations and ExecutionRecords are bound.
    """
    root = root.resolve()
    current = _git(root, "rev-parse", f"{head}^{{commit}}")
    while True:
        parents = _git(root, "rev-list", "--parents", "-n", "1", current).split()
        if len(parents) == 1:
            return current
        parent = parents[1]
        changed = _git(
            root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            parent,
            current,
        ).splitlines()
        if any(is_control_plane_path(path.strip()) for path in changed if path.strip()):
            return current
        current = parent
