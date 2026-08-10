"""Create the lab ledger bare repo with an initial main commit."""

from __future__ import annotations

import tempfile
from pathlib import Path

from cc.gitops import GIT_ENV, ensure_bare, git
from cc.home import cc_root


def seed_ledger() -> None:
    repo = "ledger"
    bare = ensure_bare(repo)
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "wt"
        git(["clone", str(bare), str(wt)])
        (wt / "README").write_text("ledger mainline\n", encoding="utf-8")
        git(["add", "README"], cwd=wt)
        git(
            [
                "-c",
                "user.name=CodeCommit Lab",
                "-c",
                "user.email=lab@local",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "initial ledger",
            ],
            cwd=wt,
        )
        git(["push", "origin", "HEAD:refs/heads/main"], cwd=wt)
    (cc_root() / "var").mkdir(parents=True, exist_ok=True)
    _ = GIT_ENV


if __name__ == "__main__":
    seed_ledger()
