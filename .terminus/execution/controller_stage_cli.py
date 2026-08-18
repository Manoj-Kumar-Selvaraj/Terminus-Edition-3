#!/usr/bin/env python3
"""Execute supported non-semantic controller stages deterministically."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

RULE_RESOLUTION_SOURCES = [
    "TERMINUS_3_AI_INSTRUCTIONS.md",
    ".terminus/AGENT_SYSTEM.md",
    ".terminus/agents/CREATION_CONTROLLER.md",
    ".terminus/agents/CREATION_PIPELINE.md",
    ".terminus/agents/PRODUCTION_AUTHENTICITY.md",
    ".terminus/reviewers/REVIEWER_CHECKLIST.md",
    ".terminus/agents/QUALITY_AGENT_REGISTRY.md",
    ".terminus/agents/STAGE_CONTRACTS.md",
    ".terminus/agents/stage_contracts.json",
]

RULE_RESOLUTION_VALIDATORS = [
    ".terminus/validate_agent_system.py",
    ".terminus/validate_stage_contracts.py",
    ".terminus/validate_task_complexity.py",
    ".terminus/validate_environment_complexity.py",
    ".terminus/validate_runtime_authenticity.py",
    ".terminus/validate_business_module_diversity.py",
    ".terminus/validate_review_freshness.py",
    ".terminus/validate_quality_interlock.py",
    ".github/workflows/terminus-edition-3-ci.yml",
    ".github/workflows/terminus-creator-complexity.yml",
    ".github/workflows/terminus-production-authenticity.yml",
]

SUPPORTED_DIRECT_STAGES = {"RULE_RESOLUTION"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _existing(paths: list[str]) -> list[str]:
    missing = [path for path in paths if not (ROOT / path).is_file()]
    if missing:
        raise ValueError(f"required controller rule/validator files are missing: {missing}")
    return paths


def _run_required_validator(path: str) -> None:
    completed = subprocess.run(
        [sys.executable, path],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"required controller validator failed: {path}")


def _flat_inputs(invocation: dict[str, Any]) -> dict[str, Any]:
    raw = invocation.get("inputs")
    if not isinstance(raw, dict):
        raise ValueError("invocation inputs are invalid")
    result: dict[str, Any] = {}
    for key in ("required", "optional"):
        values = raw.get(key, {})
        if not isinstance(values, dict):
            raise ValueError(f"invocation inputs.{key} is invalid")
        result.update(values)
    return result


def _rule_resolution(invocation: dict[str, Any]) -> dict[str, Any]:
    _run_required_validator(".terminus/validate_agent_system.py")
    sources = _existing(RULE_RESOLUTION_SOURCES)
    validators = _existing(RULE_RESOLUTION_VALIDATORS)
    authority = invocation.get("authority")
    if not isinstance(authority, dict):
        raise ValueError("invocation authority is invalid")
    control_commit = authority.get("control_plane_commit")
    task_commit = authority.get("task_commit")
    if not isinstance(control_commit, str) or not isinstance(task_commit, str):
        raise ValueError("invocation authority commits are invalid")
    inputs = _flat_inputs(invocation)
    profile = inputs.get("REQUESTED_PROFILE", "large_system_strict")
    network = inputs.get(
        "NETWORK_ENVIRONMENT_CONSTRAINTS",
        "repository-default network/environment constraints",
    )
    result = {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": task_commit,
        "status": "RULES_RESOLVED",
        "outputs": {
            "CONTROL_PLANE_COMMIT": control_commit,
            "RULE_SOURCES": sources,
            "ACTIVE_VALIDATORS": validators,
            "CREATION_PROFILE": profile,
            "NETWORK_ENVIRONMENT_CONSTRAINTS": network,
            "KNOWN_POLICY_CONFLICTS": [],
        },
        "evidence_refs": [
            {"kind": "COMMIT", "ref": f"commit:{control_commit}"},
        ],
    }
    return result


def execute(invocation: dict[str, Any]) -> dict[str, Any]:
    stage = invocation.get("stage")
    output_contract = invocation.get("output_contract")
    if not isinstance(stage, dict) or not isinstance(output_contract, dict):
        raise ValueError("invocation stage/output contract is invalid")
    stage_id = stage.get("stage_id")
    if stage.get("role_class") != "CONTROLLER":
        raise ValueError("controller-stage executor accepts CONTROLLER stages only")
    if stage_id not in SUPPORTED_DIRECT_STAGES:
        raise ValueError(f"controller stage is not registered for direct execution: {stage_id}")
    semantic_reviewers = output_contract.get("semantic_reviewers", [])
    if semantic_reviewers:
        raise ValueError("controller-stage direct execution cannot replace semantic reviewers")
    if invocation.get("readiness") != "READY":
        raise ValueError("controller-stage invocation is not READY")
    if stage_id == "RULE_RESOLUTION":
        return _rule_resolution(invocation)
    raise AssertionError(stage_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invocation", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    invocation = _load(Path(args.invocation))
    result = execute(invocation)
    _write(Path(args.output), result)
    print(
        f"Controller direct execution PASS stage={invocation['stage']['stage_id']} "
        f"invocation={invocation['invocation_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
