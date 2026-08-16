"""Bootstrap a control-plane root: catalogue repositories and seed their history.

The seeded content stands in for the settlement estate the lab mirrors: a
protected ledger with a release branch and an unprotected bench repository.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from cc.home import bare_repo_path, cc_root, ensure_layout
from cc.prs import store
from cc.repos import catalog
from cc.repos.gitops import git, init_bare, ref_commit, update_ref

LEDGER_FILES = {
    "README": "settlement ledger mainline\n",
    "settlement.cfg": "cycle=daily\nvenue=eu-west-1\nnetting=bilateral\n",
    "accounts/opening.csv": "account,currency,opening\nA-1001,EUR,0\nA-1002,GBP,0\n",
}
SANDBOX_FILES = {
    "README": "bench repository for evaluator experiments\n",
    "bench.cfg": "mode=scratch\nretention=7d\n",
}
LEDGER_BRANCHES = ("refs/heads/main", "refs/heads/release")


def _write_tree(worktree: Path, files: dict[str, str]) -> None:
    for relative, body in files.items():
        target = worktree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")


def _seed_repo(repo: str, files: dict[str, str], message: str) -> str:
    """Create the first commit of a bare repository and return its object id."""
    bare = bare_repo_path(repo)
    init_bare(bare)
    head = ref_commit(bare, "refs/heads/main")
    if head is not None:
        return head
    with tempfile.TemporaryDirectory(prefix=f"cc-seed-{repo}-") as scratch:
        worktree = Path(scratch) / "work"
        git(["clone", str(bare), str(worktree)])
        _write_tree(worktree, files)
        git(["add", "-A"], cwd=worktree)
        git(["commit", "-m", message], cwd=worktree)
        git(["push", str(bare), "HEAD:refs/heads/main"], cwd=worktree)
    landed = ref_commit(bare, "refs/heads/main")
    if landed is None:
        raise RuntimeError(f"seeding {repo} did not create refs/heads/main")
    return landed


def _ensure_branch(repo: str, ref: str, commit: str) -> None:
    bare = bare_repo_path(repo)
    if ref_commit(bare, ref) is None:
        update_ref(bare, ref, commit)


def bootstrap(force: bool = False) -> dict[str, Any]:
    """Create catalogue entries, bare repositories, and empty mutable state."""
    ensure_layout()
    catalog.register(
        "ledger",
        default_branch="refs/heads/main",
        protected_refs=LEDGER_BRANCHES,
        description="Settlement ledger; mainline and release are protected.",
    )
    catalog.register(
        "sandbox",
        default_branch="refs/heads/main",
        protected_refs=(),
        description="Bench repository used for evaluator experiments.",
    )
    if force:
        for repo in ("ledger", "sandbox"):
            _reset_repo(repo)
    ledger_head = _seed_repo("ledger", LEDGER_FILES, "initial settlement ledger")
    for ref in LEDGER_BRANCHES:
        _ensure_branch("ledger", ref, ledger_head)
    sandbox_head = _seed_repo("sandbox", SANDBOX_FILES, "initial bench tree")
    store.initialize()
    return {
        "ok": True,
        "root": str(cc_root()),
        "repos": [
            {"repo": "ledger", "head": ledger_head, "protected": list(LEDGER_BRANCHES)},
            {"repo": "sandbox", "head": sandbox_head, "protected": []},
        ],
    }


def _reset_repo(repo: str) -> None:
    """Remove a bare repository so the next bootstrap seeds it again."""
    import shutil

    bare = bare_repo_path(repo)
    if bare.exists():
        shutil.rmtree(bare)


if __name__ == "__main__":
    import json

    print(json.dumps(bootstrap(), separators=(",", ":")))
