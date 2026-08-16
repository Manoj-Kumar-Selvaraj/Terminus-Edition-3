"""Bare-repository git operations.

All repositories live as bare git directories under ``var/repos``. Every
invocation runs with a fixed identity and a disabled prompt so operator
commands behave the same way in a container as they do on a workstation.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from cc.errors import GitError, NotFound, ValidationException

IDENTITY = ("CodeCommit Lab", "lab@codecommit.local")
GIT_ENV = {
    "GIT_AUTHOR_NAME": IDENTITY[0],
    "GIT_AUTHOR_EMAIL": IDENTITY[1],
    "GIT_COMMITTER_NAME": IDENTITY[0],
    "GIT_COMMITTER_EMAIL": IDENTITY[1],
    "GIT_AUTHOR_DATE": "2026-03-02T09:15:00+0000",
    "GIT_COMMITTER_DATE": "2026-03-02T09:15:00+0000",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_CONFIG_NOSYSTEM": "1",
}
CONFIG_FLAGS = [
    "-c",
    f"user.name={IDENTITY[0]}",
    "-c",
    f"user.email={IDENTITY[1]}",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "advice.detachedHead=false",
]


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(GIT_ENV)
    env.setdefault("HOME", str(Path.home()))
    return env


def git(
    args: list[str],
    *,
    cwd: Path | None = None,
    git_dir: Path | None = None,
    check: bool = True,
) -> str:
    """Run one git command and return trimmed stdout."""
    command = ["git"]
    if git_dir is not None:
        command.extend(["--git-dir", str(git_dir)])
    command.extend(CONFIG_FLAGS)
    command.extend(args)
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    if check and completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        raise GitError(
            "GIT_COMMAND_FAILED",
            f"git {' '.join(args)} failed: {detail[-1] if detail else 'no output'}",
        )
    return completed.stdout.strip()


def init_bare(path: Path, default_branch: str = "main") -> Path:
    """Create a bare repository with a deterministic default branch."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not (path / "HEAD").is_file():
        git(["init", "--bare", f"--initial-branch={default_branch}", str(path)])
        git(["symbolic-ref", "HEAD", f"refs/heads/{default_branch}"], git_dir=path)
    return path


def require_bare(path: Path) -> Path:
    """Fail with a control-plane error when a bare repository is missing."""
    if not (path / "HEAD").is_file():
        raise NotFound("REPO_MISSING", f"no bare repository at {path}")
    return path


def clone(bare: Path, dest: Path) -> str:
    """Clone a bare repository into a fresh working tree and return its head."""
    require_bare(bare)
    if dest.exists():
        raise ValidationException("DEST_EXISTS", f"clone destination {dest} already exists")
    dest.parent.mkdir(parents=True, exist_ok=True)
    git(["clone", str(bare), str(dest)])
    return git(["rev-parse", "HEAD"], cwd=dest)


def push_head(worktree: Path, bare: Path, remote_ref: str) -> str:
    """Push the working tree head onto a remote ref and return the pushed commit."""
    require_bare(bare)
    if not (worktree / ".git").exists():
        raise ValidationException("NOT_A_WORKTREE", f"{worktree} is not a git working tree")
    commit = git(["rev-parse", "HEAD"], cwd=worktree)
    git(["push", str(bare), f"HEAD:{remote_ref}"], cwd=worktree)
    return commit


def ref_commit(bare: Path, ref: str) -> str | None:
    """Object id a ref points at, or None when the ref does not exist."""
    require_bare(bare)
    out = git(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], git_dir=bare, check=False)
    return out or None


def list_refs(bare: Path) -> dict[str, str]:
    """Every branch ref of a bare repository mapped to its object id."""
    require_bare(bare)
    out = git(["for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"], git_dir=bare)
    refs: dict[str, str] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            refs[parts[0]] = parts[1]
    return refs


def is_ancestor(bare: Path, older: str, newer: str) -> bool:
    """True when older is reachable from newer."""
    require_bare(bare)
    completed = subprocess.run(
        ["git", "--git-dir", str(bare), "merge-base", "--is-ancestor", older, newer],
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise GitError("ANCESTRY_CHECK_FAILED", completed.stderr.strip() or "merge-base failed")
    return completed.returncode == 0


def commit_parents(bare: Path, rev: str) -> list[str]:
    """Parent object ids of a commit."""
    out = git(["rev-list", "--parents", "-n", "1", rev], git_dir=bare)
    return out.split()[1:]


def commit_subject(bare: Path, rev: str) -> str:
    """First line of a commit message."""
    return git(["log", "-1", "--format=%s", rev], git_dir=bare)


def update_ref(bare: Path, ref: str, new_commit: str, old_commit: str | None = None) -> None:
    """Move a ref, optionally asserting the value it is expected to hold."""
    require_bare(bare)
    args = ["update-ref", ref, new_commit]
    if old_commit:
        args.append(old_commit)
    git(args, git_dir=bare)


def merge_ff(bare: Path, dest_ref: str, source_commit: str) -> str:
    """Advance dest_ref to source_commit and return the resulting commit.

    The destination tip must already be reachable from the source, so the ref
    moves forward without synthesising a merge commit.
    """
    require_bare(bare)
    dest_tip = ref_commit(bare, dest_ref)
    if dest_tip is None:
        raise NotFound("REF_NOT_FOUND", f"{dest_ref} does not exist")
    if dest_tip == source_commit:
        return dest_tip
    if not is_ancestor(bare, dest_tip, source_commit):
        raise ValidationException(
            "NOT_FAST_FORWARD",
            f"{dest_ref} at {dest_tip[:12]} is not an ancestor of {source_commit[:12]}",
            dest_ref=dest_ref,
            dest_commit=dest_tip,
            source_commit=source_commit,
        )
    update_ref(bare, dest_ref, source_commit, dest_tip)
    return source_commit
