from __future__ import annotations

import ipaddress
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable


GIT_ENV = {
    "GIT_AUTHOR_NAME": "CodeCommit Lab",
    "GIT_AUTHOR_EMAIL": "lab@local",
    "GIT_COMMITTER_NAME": "CodeCommit Lab",
    "GIT_COMMITTER_EMAIL": "lab@local",
    "GIT_AUTHOR_DATE": "2026-04-01T12:00:00+0000",
    "GIT_COMMITTER_DATE": "2026-04-01T12:00:00+0000",
    "GIT_TERMINAL_PROMPT": "0",
}


def full_ref(branch: str) -> str:
    branch = branch.strip()
    if branch.startswith("refs/"):
        return branch
    return f"refs/heads/{branch}"


def short_ref(ref: str) -> str:
    ref = full_ref(ref)
    prefix = "refs/heads/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def ip_in_cidrs(addr: str, cidrs: Iterable[str]) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    for c in cidrs:
        try:
            if ip in ipaddress.ip_network(c, strict=False):
                return True
        except ValueError:
            continue
    return False


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def run_git(args: list[str], cwd: Path | None = None, check: bool = True) -> str:
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
    if check and cp.returncode != 0:
        raise RuntimeError(f"git {args} failed: {cp.stderr or cp.stdout}")
    return (cp.stdout or "").strip()
