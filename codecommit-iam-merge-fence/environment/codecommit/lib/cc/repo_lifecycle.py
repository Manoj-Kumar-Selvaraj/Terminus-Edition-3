from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from cc.repos import catalog, gitops
from cc.services.validators import validate_repo_name
from cc.util import run_git


def create_repo(name: str, *, description: str = "", default_branch: str = "main") -> dict[str, Any]:
    validate_repo_name(name)
    entry = catalog.upsert_repo(name, default_branch=default_branch, description=description)
    gitops.ensure_bare(name)
    return entry


def seed_readme(name: str, text: str = "ledger mainline\n") -> str:
    gitops.ensure_bare(name)
    try:
        tip = gitops.ref_commit(name, "main")
        if tip:
            return tip
    except Exception:  # noqa: BLE001
        pass
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "wt"
        gitops.clone(name, wt)
        (wt / "README").write_text(text, encoding="utf-8")
        run_git(["add", "README"], cwd=wt)
        status = run_git(["status", "--porcelain"], cwd=wt)
        if not status.strip():
            return gitops.ref_commit(name, "main")
        run_git(["-c", "commit.gpgsign=false", "commit", "-m", "initial"], cwd=wt)
        return gitops.push(name, wt, "main")


def delete_repo_files(name: str) -> None:
    bare = gitops.ensure_bare(name)
    if bare.exists():
        shutil.rmtree(bare)
    data = catalog.store().read()
    data.get("repos", {}).pop(name, None)
    catalog.store().write(data)


def repo_status(name: str) -> dict[str, Any]:
    entry = catalog.require_repo(name)
    tip = None
    err = None
    try:
        tip = gitops.ref_commit(name, entry.get("default_branch") or "main")
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
    return {"repo": entry, "tip": tip, "error": err}


def list_detailed() -> list[dict[str, Any]]:
    return [repo_status(n) for n in catalog.list_repos()]
