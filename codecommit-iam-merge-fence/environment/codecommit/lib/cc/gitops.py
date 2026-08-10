from __future__ import annotations

import os
import subprocess
from pathlib import Path

from cc.errors import CcError
from cc.home import bare_path, full_ref

GIT_ENV = {
    "GIT_AUTHOR_NAME": "CodeCommit Lab",
    "GIT_AUTHOR_EMAIL": "lab@local",
    "GIT_COMMITTER_NAME": "CodeCommit Lab",
    "GIT_COMMITTER_EMAIL": "lab@local",
    "GIT_AUTHOR_DATE": "2026-04-01T12:00:00+0000",
    "GIT_COMMITTER_DATE": "2026-04-01T12:00:00+0000",
    "GIT_TERMINAL_PROMPT": "0",
}


def git(args: list[str], cwd: Path | None = None) -> str:
    env = os.environ.copy()
    env.update(GIT_ENV)
    cp = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if cp.returncode != 0:
        raise CcError("GitError", cp.stderr.strip()[:200] or cp.stdout.strip()[:200])
    return cp.stdout.strip()


def ensure_bare(repo: str) -> Path:
    path = bare_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not (path / "HEAD").exists():
        git(["init", "--bare", str(path)])
        git(["--git-dir", str(path), "symbolic-ref", "HEAD", "refs/heads/main"])
    return path


def clone(repo: str, dest: Path) -> None:
    dest = dest.resolve()
    if dest.exists():
        raise CcError("ValidationException", "DEST_EXISTS")
    src = ensure_bare(repo)
    git(["clone", str(src), str(dest)])


def branch_commit(worktree: Path, branch: str) -> str:
    return git(["rev-parse", full_ref(branch).removeprefix("refs/heads/")], cwd=worktree)


def push(repo: str, worktree: Path, branch: str) -> str:
    worktree = worktree.resolve()
    ref = full_ref(branch)
    short = ref.removeprefix("refs/heads/")
    git(["remote", "set-url", "origin", str(bare_path(repo))], cwd=worktree)
    git(["push", "origin", f"HEAD:{ref}"], cwd=worktree)
    return git(["--git-dir", str(bare_path(repo)), "rev-parse", ref])


def ref_commit(repo: str, ref: str) -> str:
    return git(["--git-dir", str(bare_path(repo)), "rev-parse", full_ref(ref)])


def is_ancestor(repo: str, maybe_old: str, maybe_new: str) -> bool:
    env = os.environ.copy()
    env.update(GIT_ENV)
    cp = subprocess.run(
        ["git", "--git-dir", str(bare_path(repo)), "merge-base", "--is-ancestor", maybe_old, maybe_new],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return cp.returncode == 0


def merge_ff(repo: str, source_ref: str, dest_ref: str) -> str:
    dest_ref = full_ref(dest_ref)
    source_ref = full_ref(source_ref)
    src = ref_commit(repo, source_ref)
    dest = ref_commit(repo, dest_ref)
    # Broken: always create a merge commit, even when a fast-forward exists.
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "wt"
        git(["clone", str(bare_path(repo)), str(wt)])
        git(["checkout", dest_ref.removeprefix("refs/heads/")], cwd=wt)
        git(["fetch", "origin", source_ref.removeprefix("refs/heads/")], cwd=wt)
        git(["merge", "--no-ff", "-m", f"Merge {source_ref} into {dest_ref}", "FETCH_HEAD"], cwd=wt)
        git(["push", "origin", f"HEAD:{dest_ref}"], cwd=wt)
        return git(["rev-parse", "HEAD"], cwd=wt)


def update_ff(repo: str, source_commit: str, dest_ref: str) -> str:
    dest_ref = full_ref(dest_ref)
    dest = ref_commit(repo, dest_ref)
    if dest != source_commit and not is_ancestor(repo, dest, source_commit):
        raise CcError("ValidationException", "NOT_FAST_FORWARD")
    git(["--git-dir", str(bare_path(repo)), "update-ref", dest_ref, source_commit])
    return source_commit
