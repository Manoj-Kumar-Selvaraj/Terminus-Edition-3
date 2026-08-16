"""Filesystem layout and configuration loading for one control-plane root.

Every path is derived from ``CC_ROOT`` at call time so a single installation can
serve several isolated roots in the same process.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_ROOT = "/app/codecommit"
ARN_TEMPLATE = "arn:aws:codecommit:{region}:{account}:{repo}"

TRIGGER_KEYS = ["event_id", "repo", "ref", "commit", "pipeline", "status"]
AUDIT_KEYS = [
    "seq",
    "principal",
    "action",
    "repo",
    "ref",
    "decision",
    "reason",
    "source_ip",
    "mfa",
]
OUTBOX_KEYS = [
    "outbox_id",
    "event_id",
    "endpoint",
    "pipeline",
    "repo",
    "ref",
    "commit",
    "status",
    "attempts",
    "next_tick",
]


def cc_root() -> Path:
    return Path(os.environ.get("CC_ROOT", DEFAULT_ROOT))


def ops_dir() -> Path:
    return cc_root() / "ops"


def policies_dir() -> Path:
    return cc_root() / "policies"


def var_dir() -> Path:
    return cc_root() / "var"


def log_dir() -> Path:
    return cc_root() / "log"


def repos_dir() -> Path:
    return var_dir() / "repos"


def bare_repo_path(repo: str) -> Path:
    return repos_dir() / f"{repo}.git"


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


def sinks_dir() -> Path:
    return var_dir() / "sinks"


def locks_dir() -> Path:
    return var_dir() / "locks"


def ensure_layout() -> None:
    """Create the mutable state directories this root needs."""
    for path in (var_dir(), repos_dir(), sinks_dir(), locks_dir()):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        if default is None:
            raise FileNotFoundError(str(path))
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _principal_file() -> dict[str, Any]:
    return read_json(ops_dir() / "principals.json", {})


def account_id() -> str:
    return str(_principal_file().get("account", "000000000000"))


def region() -> str:
    return str(_principal_file().get("region", "eu-west-1"))


def principals() -> dict[str, Any]:
    """Principal catalog keyed by principal id."""
    body = _principal_file()
    catalog = body.get("principals")
    if isinstance(catalog, dict):
        return catalog
    return {}


def principal(name: str) -> dict[str, Any] | None:
    return principals().get(name)


def attached_policies(name: str) -> list[str]:
    entry = principal(name) or {}
    return [str(item) for item in entry.get("policies") or []]


def policy_document(policy_id: str) -> dict[str, Any]:
    path = policies_dir() / f"{policy_id}.json"
    return read_json(path, {})


def approval_rules() -> list[dict[str, Any]]:
    body = read_json(ops_dir() / "approval-rules.json", {})
    rules = body.get("rules")
    return list(rules) if isinstance(rules, list) else []


def pipeline_bindings() -> list[dict[str, Any]]:
    body = read_json(ops_dir() / "pipelines.json", {})
    bindings = body.get("bindings")
    return list(bindings) if isinstance(bindings, list) else []


def webhook_endpoints() -> list[dict[str, Any]]:
    body = read_json(ops_dir() / "webhooks.json", {})
    endpoints = body.get("endpoints")
    return list(endpoints) if isinstance(endpoints, list) else []


def repo_arn(repo: str) -> str:
    return ARN_TEMPLATE.format(region=region(), account=account_id(), repo=repo)


def resolve_sink(relative: str) -> Path:
    """Resolve an endpoint sink path relative to this control-plane root."""
    candidate = Path(relative)
    if candidate.is_absolute():
        return candidate
    return cc_root() / candidate
