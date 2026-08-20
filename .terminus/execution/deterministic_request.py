#!/usr/bin/env python3
"""Build and validate repository-native deterministic-validation dispatch requests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

STAGE_ID = "DETERMINISTIC_VALIDATION"
SCHEMA_VERSION = "1.0"
_REQUEST_ID = re.compile(r"^detreq_[0-9a-f]{64}$")
_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_COMMIT = re.compile(r"^[0-9a-f]{40,64}$")


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _require_commit(root: Path, value: Any, label: str) -> str:
    if not isinstance(value, str) or not _COMMIT.fullmatch(value):
        raise ValueError(f"{label} must be a full hexadecimal Git commit")
    subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{value}^{{commit}}"],
        check=True,
        capture_output=True,
    )
    return value


def build_request(
    root: Path,
    *,
    task_id: str,
    task_commit: str,
    control_plane_commit: str,
    expected_repository_head: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if not _TASK_ID.fullmatch(task_id):
        raise ValueError("unsafe task_id")
    task_commit = _require_commit(root, task_commit, "task_commit")
    control_plane_commit = _require_commit(root, control_plane_commit, "control_plane_commit")
    repository_head = _require_commit(
        root,
        expected_repository_head or _git(root, "rev-parse", "HEAD^{commit}"),
        "expected_repository_head",
    )
    task_tree = _git(root, "rev-parse", f"{task_commit}:{task_id}")
    head_tree = _git(root, "rev-parse", f"{repository_head}:{task_id}")
    if task_tree != head_tree:
        raise ValueError("expected_repository_head does not contain the exact requested task snapshot")

    identity = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "stage_id": STAGE_ID,
        "task_commit": task_commit,
        "expected_repository_head": repository_head,
        "control_plane_commit": control_plane_commit,
        "evidence_contract": {
            "oracle_reward": 1,
            "nop_reward": 0,
            "require_f2p_empirical_matrix": True,
            "require_p2p_empirical_matrix": True,
        },
    }
    request_id = "detreq_" + hashlib.sha256(_canonical(identity)).hexdigest()
    return {"request_id": request_id, **identity}


def validate_request(
    root: Path,
    request: Mapping[str, Any],
    *,
    request_base: str,
) -> dict[str, Any]:
    root = root.resolve()
    expected_keys = {
        "request_id",
        "schema_version",
        "task_id",
        "stage_id",
        "task_commit",
        "expected_repository_head",
        "control_plane_commit",
        "evidence_contract",
    }
    if set(request) != expected_keys:
        raise ValueError("deterministic request key drift")
    if request.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported deterministic request schema")
    task_id = request.get("task_id")
    if not isinstance(task_id, str) or not _TASK_ID.fullmatch(task_id):
        raise ValueError("unsafe task_id")
    if request.get("stage_id") != STAGE_ID:
        raise ValueError("deterministic request is not scoped to DETERMINISTIC_VALIDATION")

    task_commit = _require_commit(root, request.get("task_commit"), "task_commit")
    expected_head = _require_commit(
        root, request.get("expected_repository_head"), "expected_repository_head"
    )
    control_commit = _require_commit(
        root, request.get("control_plane_commit"), "control_plane_commit"
    )
    request_base = _require_commit(root, request_base, "request_base")
    if request_base != expected_head:
        raise ValueError("request branch/base mismatch")

    evidence_contract = request.get("evidence_contract")
    expected_contract = {
        "oracle_reward": 1,
        "nop_reward": 0,
        "require_f2p_empirical_matrix": True,
        "require_p2p_empirical_matrix": True,
    }
    if evidence_contract != expected_contract:
        raise ValueError("deterministic evidence contract drift")

    identity = dict(request)
    request_id = identity.pop("request_id", None)
    expected_id = "detreq_" + hashlib.sha256(_canonical(identity)).hexdigest()
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id) or request_id != expected_id:
        raise ValueError("deterministic request_id is invalid")

    task_tree = _git(root, "rev-parse", f"{task_commit}:{task_id}")
    head_tree = _git(root, "rev-parse", f"{expected_head}:{task_id}")
    if task_tree != head_tree:
        raise ValueError("deterministic request task snapshot is stale")

    return {
        "request_id": request_id,
        "task_id": task_id,
        "task_commit": task_commit,
        "expected_repository_head": expected_head,
        "control_plane_commit": control_commit,
        "task_tree": task_tree,
        "stage_id": STAGE_ID,
    }


def dispatch_envelope(request: Mapping[str, Any]) -> dict[str, Any]:
    request_id = str(request["request_id"])
    suffix = request_id.removeprefix("detreq_")[:16]
    task_id = str(request["task_id"])
    return {
        "status": "READY_TO_DISPATCH",
        "stage_id": STAGE_ID,
        "execution_mode": "HOSTED_DETERMINISTIC_VALIDATION",
        "workflow": ".github/workflows/terminus-deterministic-request.yml",
        "trigger": "REQUEST_BRANCH_PUSH",
        "branch": f"terminus-deterministic-request/{task_id}/{suffix}",
        "request_path": f".terminus/deterministic-requests/{task_id}-{suffix}.json",
        "request": dict(request),
        "polling_policy": "poll the exact workflow run triggered by the request commit; do not redispatch while queued or in_progress",
        "evidence_policy": "accept only artifact/run evidence that rebinds the exact request_id, task_commit and control_plane_commit",
    }


def _write(value: Mapping[str, Any], output: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("--task-id", required=True)
    build.add_argument("--task-commit", required=True)
    build.add_argument("--control-plane-commit", required=True)
    build.add_argument("--expected-repository-head")
    build.add_argument("--output")

    validate = sub.add_parser("validate")
    validate.add_argument("--request", required=True)
    validate.add_argument("--request-base", required=True)
    validate.add_argument("--output")

    dispatch = sub.add_parser("dispatch")
    dispatch.add_argument("--request", required=True)
    dispatch.add_argument("--output")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "build":
        value = build_request(
            root,
            task_id=args.task_id,
            task_commit=args.task_commit,
            control_plane_commit=args.control_plane_commit,
            expected_repository_head=args.expected_repository_head,
        )
    else:
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise ValueError("request must contain one JSON object")
        if args.command == "validate":
            value = validate_request(root, request, request_base=args.request_base)
        else:
            value = dispatch_envelope(request)
    _write(value, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
