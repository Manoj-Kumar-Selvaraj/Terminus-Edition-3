#!/usr/bin/env python3
"""Evaluate a five-trial Harbor difficulty suite from reward.txt files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_reward(path: Path) -> float:
    raw = path.read_text(encoding="utf-8").strip()
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid reward in {path}: {raw!r}") from exc


def classify(passes: int, total: int, expected: int) -> tuple[str, str, int]:
    if total != expected:
        return (
            "incomplete",
            f"expected {expected} trials but found {total}; do not calibrate difficulty",
            22,
        )
    if passes == 0:
        return (
            "trajectory_review_required",
            "0/5 passed; inspect all solver trajectories for instruction, environment, or verifier gaps before accepting difficulty",
            21,
        )
    if passes >= 4:
        return (
            "too_easy",
            f"{passes}/{total} passed; at least two trials must fail, so recalibration is required",
            20,
        )
    return (
        "target_band",
        f"{passes}/{total} passed and {total - passes}/{total} failed; current difficulty policy is satisfied",
        0,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite_dir", type=Path)
    parser.add_argument("--expected", type=int, default=5)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    reward_files = sorted(args.suite_dir.rglob("reward.txt"))
    rewards = []
    for path in reward_files:
        reward = parse_reward(path)
        rewards.append({"path": str(path), "reward": reward, "passed": reward >= 1.0})

    passes = sum(1 for item in rewards if item["passed"])
    total = len(rewards)
    status, message, exit_code = classify(passes, total, args.expected)

    payload = {
        "suite_dir": str(args.suite_dir),
        "expected_trials": args.expected,
        "trials_found": total,
        "passes": passes,
        "failures": total - passes,
        "status": status,
        "message": message,
        "rewards": rewards,
    }

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")

    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Difficulty suite result",
            "",
            f"- Status: **{status}**",
            f"- Passes: **{passes}/{total}**",
            f"- Failures: **{total - passes}/{total}**",
            f"- Decision: {message}",
            "",
            "## Trials",
            "",
        ]
        for index, item in enumerate(rewards, start=1):
            result = "PASS" if item["passed"] else "FAIL"
            lines.append(f"- Trial {index}: {result} (reward={item['reward']}) — `{item['path']}`")
        args.markdown_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
