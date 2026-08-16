from __future__ import annotations

import os
from pathlib import Path


def root() -> Path:
    return Path(os.environ.get("CC_ROOT", "/app/codecommit")).resolve()


def lib_dir() -> Path:
    return root() / "lib"


def ops_dir() -> Path:
    return root() / "ops"


def policies_dir() -> Path:
    return root() / "policies"


def var_dir() -> Path:
    return root() / "var"


def repos_dir() -> Path:
    return var_dir() / "repos"


def docs_dir() -> Path:
    return root() / "docs"


def log_dir() -> Path:
    return root() / "log"


def principals_path() -> Path:
    return ops_dir() / "principals.json"


def approval_rules_path() -> Path:
    return ops_dir() / "approval-rules.json"


def pipelines_path() -> Path:
    return ops_dir() / "pipelines.json"


def webhooks_path() -> Path:
    return ops_dir() / "webhooks.json"


def catalog_path() -> Path:
    return var_dir() / "catalog.json"


def prs_path() -> Path:
    return var_dir() / "prs.json"


def triggers_path() -> Path:
    return var_dir() / "triggers.jsonl"


def audit_path() -> Path:
    return var_dir() / "audit.jsonl"


def outbox_path() -> Path:
    return var_dir() / "outbox.jsonl"


def bare_repo(name: str) -> Path:
    return repos_dir() / f"{name}.git"


def ensure_layout() -> None:
    for p in (ops_dir(), policies_dir(), var_dir(), repos_dir(), docs_dir(), log_dir()):
        p.mkdir(parents=True, exist_ok=True)
