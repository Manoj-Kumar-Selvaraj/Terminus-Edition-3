from __future__ import annotations

from pathlib import Path

from cc import home
from cc.util import full_ref, run_git, short_ref


def ensure_bare(name: str) -> Path:
    home.ensure_layout()
    bare = home.bare_repo(name)
    if not (bare / "HEAD").exists():
        bare.mkdir(parents=True, exist_ok=True)
        run_git(["init", "--bare", str(bare)])
        run_git(["--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"])
    return bare


def clone(name: str, dest: Path) -> None:
    bare = ensure_bare(name)
    if dest.exists():
        raise FileExistsError(str(dest))
    run_git(["clone", str(bare), str(dest)])


def push(name: str, worktree: Path, branch: str) -> str:
    bare = ensure_bare(name)
    ref = full_ref(branch)
    short = short_ref(branch)
    run_git(["remote", "set-url", "origin", str(bare)], cwd=worktree)
    # ensure branch exists locally
    run_git(["rev-parse", "--verify", short], cwd=worktree)
    run_git(["push", "origin", f"HEAD:{ref}"], cwd=worktree)
    return ref_commit(name, ref)


def ref_commit(name: str, ref: str) -> str:
    bare = ensure_bare(name)
    ref = full_ref(ref)
    return run_git(["--git-dir", str(bare), "rev-parse", ref])


def is_ancestor(name: str, maybe_ancestor: str, tip: str) -> bool:
    bare = ensure_bare(name)
    out = run_git(
        ["--git-dir", str(bare), "merge-base", "--is-ancestor", maybe_ancestor, tip],
        check=False,
    )
    # merge-base --is-ancestor returns exit code; run_git with check=False still returns stdout
    import os
    import subprocess

    env = os.environ.copy()
    from cc.util import GIT_ENV

    env.update(GIT_ENV)
    cp = subprocess.run(
        ["git", "--git-dir", str(bare), "merge-base", "--is-ancestor", maybe_ancestor, tip],
        capture_output=True,
        text=True,
        env=env,
    )
    return cp.returncode == 0


def parents(name: str, rev: str) -> list[str]:
    bare = ensure_bare(name)
    out = run_git(["--git-dir", str(bare), "rev-list", "--parents", "-n", "1", rev])
    parts = out.split()
    return parts[1:]


def merge_ff_broken(name: str, source_commit: str, dest_ref: str) -> str:
    """Broken: always create a merge commit via a temporary worktree."""
    import tempfile

    bare = ensure_bare(name)
    dest_ref = full_ref(dest_ref)
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "wt"
        run_git(["clone", str(bare), str(wt)])
        run_git(["checkout", "-B", short_ref(dest_ref), dest_ref], cwd=wt)
        run_git(["-c", "commit.gpgsign=false", "merge", "--no-ff", "-m", "merge", source_commit], cwd=wt)
        run_git(["push", "origin", f"HEAD:{dest_ref}"], cwd=wt)
        return ref_commit(name, dest_ref)


def update_ff(name: str, source_commit: str, dest_ref: str) -> str:
    bare = ensure_bare(name)
    dest_ref = full_ref(dest_ref)
    dest_head = ref_commit(name, dest_ref)
    if not is_ancestor(name, dest_head, source_commit):
        from cc.errors import ValidationException

        raise ValidationException(code="NOT_FAST_FORWARD")
    run_git(["--git-dir", str(bare), "update-ref", dest_ref, source_commit])
    return source_commit
