#!/usr/bin/env python3
"""Fail closed before dispatching a Terminus semantic review packet.

A review packet may be executed only while it still names the current task commit,
its role contract/scope are current, and its immutable result path is unused.
This is an invocation-time guard; validate_review_freshness.py remains the
post-result gate validator.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from review_contract import (
    ROLE_POLICY_VERSIONS,
    current_task_commit,
    policy_versions,
    review_scope_hash,
    role_contract_hash,
    task_tree_dirty,
    validate_schema,
)

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
SCHEMAS = T / "agents" / "schemas"


def set_root(root: Path) -> None:
    global ROOT, T, SCHEMAS
    ROOT = root.resolve()
    T = ROOT / ".terminus"
    SCHEMAS = T / "agents" / "schemas"


def _safe_repo_path(relative: str, problems: list[str], label: str) -> Path | None:
    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        problems.append(f"{label} escapes repository: {relative}")
        return None
    return candidate


def _load_packet(packet_path: Path, problems: list[str]) -> dict | None:
    try:
        relative = packet_path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        problems.append(f"packet path escapes repository: {packet_path}")
        return None
    if not str(relative).startswith(".terminus/reviews/") or not str(relative).endswith(
        ".packet.json"
    ):
        problems.append("packet must be an immutable .terminus/reviews/.../*.packet.json file")
        return None
    if not packet_path.is_file():
        problems.append(f"packet does not exist: {relative}")
        return None
    try:
        data = json.loads(packet_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        problems.append(f"invalid packet JSON: {exc}")
        return None
    if not isinstance(data, dict):
        problems.append("packet must contain a JSON object")
        return None

    schema_path = SCHEMAS / "context_packet.schema.json"
    if not schema_path.is_file():
        problems.append("context packet schema is unavailable")
        return None
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate_schema(data, schema, "packet", problems)
    return data


def validate_invocation(packet_path: Path) -> list[str]:
    problems: list[str] = []
    packet = _load_packet(packet_path, problems)
    if packet is None or problems:
        return problems

    task = str(packet["task"])
    task_root = ROOT / task
    if not (task_root / "task.toml").is_file():
        problems.append(f"packet task no longer exists: {task}")
        return problems
    if task_tree_dirty(ROOT, task):
        problems.append(f"task tree is dirty; refuse semantic review dispatch for {task}")

    truth_commit = current_task_commit(ROOT, task)
    if not truth_commit:
        problems.append(f"cannot resolve current task commit for {task}")
    elif packet["task_commit"] != truth_commit:
        problems.append(
            "stale packet task_commit: "
            f"packet={str(packet['task_commit'])[:12]} current={truth_commit[:12]}"
        )

    role = str(packet["role"])
    versions = policy_versions(ROOT)
    if packet["protocol_policy_version"] != versions["protocol"]:
        problems.append(
            "stale packet protocol policy: "
            f"packet={packet['protocol_policy_version']} current={versions['protocol']}"
        )
    if packet["prompt_policy_version"] != versions["prompts"]:
        problems.append(
            "stale packet prompt policy: "
            f"packet={packet['prompt_policy_version']} current={versions['prompts']}"
        )
    expected_role_policy = ROLE_POLICY_VERSIONS.get(role)
    if expected_role_policy is None:
        problems.append(f"unknown reviewer role: {role}")
    elif packet["role_policy_version"] != expected_role_policy:
        problems.append(
            "stale packet role policy: "
            f"packet={packet['role_policy_version']} current={expected_role_policy}"
        )

    current_contract = role_contract_hash(ROOT, role)
    if packet["role_contract_hash"] != current_contract:
        problems.append(
            "stale packet role contract: "
            f"packet={str(packet['role_contract_hash'])[:12]} current={current_contract[:12]}"
        )

    current_scope = review_scope_hash(ROOT, task, role)
    packet_scope = str(packet.get("review_scope_hash", ""))
    if current_scope != packet_scope:
        problems.append(
            "stale packet review scope: "
            f"packet={packet_scope[:12] or '<none>'} current={current_scope[:12] or '<none>'}"
        )

    packet_rel = packet_path.resolve().relative_to(ROOT.resolve())
    expected_output_rel = str(packet_rel).replace(".packet.json", ".json")
    output_rel = str(packet["review_output_path"])
    if output_rel != expected_output_rel:
        problems.append(
            f"packet review_output_path mismatch: packet={output_rel} expected={expected_output_rel}"
        )
    output_path = _safe_repo_path(output_rel, problems, "review_output_path")
    if output_path is not None and output_path.exists():
        problems.append(
            "immutable review output already exists; generate a new packet/review ID instead of rerunning: "
            f"{output_rel}"
        )

    expected_parent = Path(".terminus") / "reviews" / task / str(packet["task_commit"])[:8]
    if packet_rel.parent != expected_parent:
        problems.append(
            f"packet is filed under {packet_rel.parent}, expected {expected_parent} for its task commit"
        )

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path, help="repository-relative *.packet.json path")
    args = parser.parse_args(argv)

    packet_path = args.packet if args.packet.is_absolute() else ROOT / args.packet
    problems = validate_invocation(packet_path)
    if problems:
        print("REVIEW_INVOCATION_BLOCKED")
        for problem in problems:
            print(f"- {problem}")
        return 1

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    print("REVIEW_INVOCATION_READY")
    print(f"review_id={packet['review_id']}")
    print(f"role={packet['role']}")
    print(f"task={packet['task']}")
    print(f"task_commit={packet['task_commit']}")
    print(f"review_output={packet['review_output_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
