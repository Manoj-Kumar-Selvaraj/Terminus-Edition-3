#!/usr/bin/env python3
"""Classify later reviewer findings against the task diff after an exhaustive review."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def prior_exhaustive(data: dict) -> bool:
    ex = data.get("role_output", {}).get("EXHAUSTIVENESS", {})
    expected = {
        "REQUIREMENTS_ENUMERATED": "COMPLETE",
        "VERIFIER_BEHAVIORS_ENUMERATED": "COMPLETE",
        "FORWARD_MATRIX_COMPLETE": "YES",
        "REVERSE_MATRIX_COMPLETE": "YES",
        "DELEGATED_CONTRACTS_COMPLETE": "YES",
        "P2P_BOUNDARIES_COMPLETE": "YES",
        "F2P_BOUNDARIES_COMPLETE": "YES",
        "OUTPUT_INTERFACES_COMPLETE": "YES",
        "SECOND_PASS_OMISSION_SWEEP": "PASS",
    }
    return all(ex.get(key) == value for key, value in expected.items()) and not ex.get(
        "UNINSPECTED_SCOPE"
    )


def task_ref(ref: str, task: str) -> str:
    base = ref.split("@", 1)[0].split("#", 1)[0]
    prefix = f"{task}/"
    return base if base.startswith(prefix) else ""


def changed_paths(prior_commit: str, current_commit: str, task: str) -> set[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", prior_commit, current_commit, "--", task],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prior_review", type=Path)
    parser.add_argument("current_review", type=Path)
    parser.add_argument("--fail-on-latent", action="store_true")
    args = parser.parse_args(argv)

    prior = load(args.prior_review)
    current = load(args.current_review)
    if prior.get("role") != current.get("role"):
        raise SystemExit("reviews must have the same role")
    if prior.get("task") != current.get("task"):
        raise SystemExit("reviews must have the same task")

    task = str(current["task"])
    changed = changed_paths(str(prior["task_commit"]), str(current["task_commit"]), task)
    exhaustive = prior_exhaustive(prior)
    classifications: list[dict[str, object]] = []
    latent = False

    for finding in current.get("findings", []):
        refs = sorted(
            {task_ref(str(ref), task) for ref in finding.get("evidence_refs", [])} - {""}
        )
        touched = sorted(set(refs) & changed)
        if exhaustive and refs and not touched:
            classification = "LATENT_REVIEWER_OMISSION"
            latent = True
        elif touched:
            classification = "TOUCHED_BY_REPAIR"
        else:
            classification = "UNKNOWN"
        classifications.append(
            {
                "finding_id": finding.get("id"),
                "classification": classification,
                "task_evidence_refs": refs,
                "touched_paths": touched,
            }
        )

    output = {
        "task": task,
        "role": current.get("role"),
        "prior_task_commit": prior.get("task_commit"),
        "current_task_commit": current.get("task_commit"),
        "prior_exhaustiveness_complete": exhaustive,
        "changed_task_paths": sorted(changed),
        "findings": classifications,
        "requires_adjudication": latent,
    }
    print(json.dumps(output, indent=2))
    return 3 if latent and args.fail_on_latent else 0


if __name__ == "__main__":
    sys.exit(main())
