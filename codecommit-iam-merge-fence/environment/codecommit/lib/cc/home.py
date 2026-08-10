from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def cc_root() -> Path:
    return Path(os.environ.get("CC_ROOT", "/app/codecommit"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def principals() -> dict[str, Any]:
    return load_json(cc_root() / "ops" / "principals.json")


def approval_rules() -> list[dict[str, Any]]:
    return load_json(cc_root() / "ops" / "approval-rules.json")["rules"]


def pipeline_bindings() -> list[dict[str, Any]]:
    return load_json(cc_root() / "ops" / "pipelines.json")["bindings"]


def policy_doc(policy_id: str) -> dict[str, Any]:
    return load_json(cc_root() / "policies" / f"{policy_id}.json")


def repo_arn(repo: str) -> str:
    return f"arn:local:codecommit:local:000000000000:{repo}"


def bare_path(repo: str) -> Path:
    return cc_root() / "var" / "repos" / f"{repo}.git"


def pr_store_path() -> Path:
    return cc_root() / "var" / "prs.json"


def trigger_path() -> Path:
    return cc_root() / "var" / "triggers.jsonl"


def full_ref(ref: str) -> str:
    if ref.startswith("refs/"):
        return ref
    return f"refs/heads/{ref}"
