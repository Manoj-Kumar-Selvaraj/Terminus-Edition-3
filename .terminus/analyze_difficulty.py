#!/usr/bin/env python3
"""Analyze Harbor difficulty trials, including per-test solvability coverage.

Edition 3 final difficulty is measured across ten agent runs: GPT-5.5 x5 plus
Claude Opus 4.8 x5. Individual five-run model suites are useful diagnostics but
are not final difficulty decisions by themselves.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

PASS_STATES = {"PASSED", "XPASS"}
TERMINAL_STATES = PASS_STATES | {"FAILED", "ERROR", "SKIPPED", "XFAIL"}
TEXT_SUFFIXES = {".log", ".txt", ".out"}
NODEID_STATUS_RE = re.compile(
    r"(?P<nodeid>(?:[^\s:]+\.py::)+[^\s]+)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b"
)
STATUS_NODEID_RE = re.compile(
    r"\b(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(?P<nodeid>(?:[^\s:]+\.py::)+[^\s]+)"
)


def parse_reward(path: Path) -> float:
    raw = path.read_text(encoding="utf-8").strip()
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid reward in {path}: {raw!r}") from exc


def discover_declared_tests(tests_dir: Path | None) -> list[str]:
    """Return verifier test function/method names declared in Python sources."""
    if tests_dir is None or not tests_dir.is_dir():
        return []

    names: set[str] = set()
    for path in sorted(tests_dir.rglob("test*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                names.add(node.name)
    return sorted(names)


def normalize_nodeid(nodeid: str) -> str:
    """Return the pytest test leaf, preserving a parametrized case suffix."""
    return nodeid.rsplit("::", 1)[-1]


def parse_junit_file(path: Path) -> dict[str, set[str]]:
    results: dict[str, set[str]] = defaultdict(set)
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return results

    for testcase in root.iter("testcase"):
        name = testcase.attrib.get("name", "")
        if not name.startswith("test_"):
            continue
        status = "PASSED"
        if testcase.find("failure") is not None:
            status = "FAILED"
        elif testcase.find("error") is not None:
            status = "ERROR"
        elif testcase.find("skipped") is not None:
            status = "SKIPPED"
        results[name].add(status)
    return results


def parse_text_file(path: Path) -> dict[str, set[str]]:
    results: dict[str, set[str]] = defaultdict(set)
    try:
        if path.stat().st_size > 8 * 1024 * 1024:
            return results
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return results

    for regex in (NODEID_STATUS_RE, STATUS_NODEID_RE):
        for match in regex.finditer(text):
            status = match.group("status")
            if status not in TERMINAL_STATES:
                continue
            name = normalize_nodeid(match.group("nodeid"))
            if name.startswith("test_"):
                results[name].add(status)
    return results


def merge_results(target: dict[str, set[str]], source: dict[str, set[str]]) -> None:
    for name, statuses in source.items():
        target[name].update(statuses)


def trial_root_for_reward(reward_file: Path, suite_dir: Path) -> Path:
    """Use the Harbor job directory containing the reward as trial evidence root."""
    current = reward_file.parent
    while current != suite_dir and current.parent != suite_dir:
        if current.name in {"verifier", "agent", "oracle"}:
            return current.parent
        current = current.parent
    return reward_file.parent


def collect_trial_test_results(trial_root: Path) -> dict[str, set[str]]:
    results: dict[str, set[str]] = defaultdict(set)
    for path in sorted(trial_root.rglob("*.xml")):
        merge_results(results, parse_junit_file(path))
    for path in sorted(trial_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        merge_results(results, parse_text_file(path))
    return results


def expand_expected_tests(declared: list[str], observed: set[str]) -> list[str]:
    """Expand declared pytest functions into observed parametrized cases when present."""
    expected: list[str] = []
    for base in declared:
        variants = sorted(name for name in observed if name.startswith(base + "["))
        if variants:
            expected.extend(variants)
        else:
            expected.append(base)
    return expected


def tier_for_rate(rate: float) -> str:
    if rate >= 1.0:
        return "too_easy_reject"
    if rate >= 0.8:
        return "base"
    if rate >= 0.5:
        return "core"
    if rate >= 0.2:
        return "advanced"
    return "frontier"


def classify(
    *,
    complete_run_passes: int,
    trials_found: int,
    expected_trials: int,
    expected_tests: list[str],
    test_coverage: dict[str, dict[str, int | bool]],
) -> tuple[str, str, int]:
    if trials_found != expected_trials:
        return (
            "incomplete",
            f"expected {expected_trials} trials but found {trials_found}; do not calibrate difficulty",
            22,
        )

    if not expected_tests:
        return (
            "test_inventory_missing",
            "could not determine verifier test cases; per-test solvability cannot be evaluated",
            23,
        )

    # A single five-run model suite is diagnostic only. A test may be 0/5 for one
    # model and still satisfy the official solvability criterion across all 10
    # GPT+Claude runs, so do not reject a task from one partial suite alone.
    if expected_trials < 10:
        rate = complete_run_passes / trials_found if trials_found else 0.0
        return (
            "partial_suite",
            f"diagnostic {trials_found}-run model suite complete ({complete_run_passes}/{trials_found} full passes, {rate:.0%}); combine both five-run model suites before final difficulty/solvability decisions",
            0,
        )

    zero_pass_tests = [
        name for name in expected_tests if int(test_coverage[name]["passes"]) == 0
    ]
    if zero_pass_tests:
        return (
            "test_case_review_required",
            f"at least one verifier test case passed in 0/{expected_trials} agent trials; inspect trajectories and remediate before acceptance: "
            + ", ".join(zero_pass_tests),
            21,
        )

    rate = complete_run_passes / trials_found
    tier = tier_for_rate(rate)
    if tier == "too_easy_reject":
        return (
            tier,
            f"{complete_run_passes}/{trials_found} complete runs passed (100%); current Edition 3 policy rejects tasks that never fail",
            20,
        )

    return (
        tier,
        f"{complete_run_passes}/{trials_found} complete runs passed ({rate:.0%}); measured tier={tier}, and every verifier test case passed at least once across the {expected_trials} trials",
        0,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite_dirs", type=Path, nargs="+")
    parser.add_argument("--expected", type=int, default=10)
    parser.add_argument("--tests-dir", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    suite_dirs = [path.resolve() for path in args.suite_dirs]
    tests_dir = args.tests_dir
    if tests_dir is None and suite_dirs:
        # CI diagnostic layout is commonly .../<task>/<suite-command>.
        inferred = Path.cwd() / suite_dirs[0].parent.name / "tests"
        if inferred.is_dir():
            tests_dir = inferred

    declared_tests = discover_declared_tests(tests_dir)
    trials: list[dict[str, object]] = []
    seen_reward_paths: set[Path] = set()
    all_observed_tests: set[str] = set()

    for suite_dir in suite_dirs:
        for reward_file in sorted(suite_dir.rglob("reward.txt")):
            resolved_reward = reward_file.resolve()
            if resolved_reward in seen_reward_paths:
                continue
            seen_reward_paths.add(resolved_reward)
            reward = parse_reward(reward_file)
            trial_root = trial_root_for_reward(reward_file, suite_dir)
            test_results = collect_trial_test_results(trial_root)
            all_observed_tests.update(test_results)
            trials.append(
                {
                    "suite_dir": str(suite_dir),
                    "reward_path": str(reward_file),
                    "trial_root": str(trial_root),
                    "reward": reward,
                    "complete_run_passed": reward >= 1.0,
                    "test_results": {
                        name: sorted(statuses) for name, statuses in sorted(test_results.items())
                    },
                }
            )

    expected_tests = expand_expected_tests(declared_tests, all_observed_tests)
    per_test_trial_passes: dict[str, int] = defaultdict(int)
    per_test_trial_observed: dict[str, int] = defaultdict(int)
    per_test_mixed: dict[str, int] = defaultdict(int)

    for trial in trials:
        test_results = trial["test_results"]
        assert isinstance(test_results, dict)
        for name in expected_tests:
            statuses = set(test_results.get(name, []))
            if statuses:
                per_test_trial_observed[name] += 1
            if statuses & PASS_STATES:
                per_test_trial_passes[name] += 1
            if statuses & PASS_STATES and statuses - PASS_STATES:
                per_test_mixed[name] += 1

    complete_run_passes = sum(1 for trial in trials if trial["complete_run_passed"])
    trials_found = len(trials)

    test_coverage: dict[str, dict[str, int | bool]] = {}
    for name in expected_tests:
        passes = per_test_trial_passes[name]
        observed = per_test_trial_observed[name]
        test_coverage[name] = {
            "passes": passes,
            "failures_or_not_observed": args.expected - passes,
            "trials_with_explicit_result": observed,
            "mixed_result_trials": per_test_mixed[name],
            "zero_pass": passes == 0,
        }

    status, message, exit_code = classify(
        complete_run_passes=complete_run_passes,
        trials_found=trials_found,
        expected_trials=args.expected,
        expected_tests=expected_tests,
        test_coverage=test_coverage,
    )

    pass_rate = complete_run_passes / trials_found if trials_found else None
    payload = {
        "suite_dirs": [str(path) for path in suite_dirs],
        "tests_dir": str(tests_dir) if tests_dir else None,
        "expected_trials": args.expected,
        "trials_found": trials_found,
        "complete_run_passes": complete_run_passes,
        "complete_run_failures": trials_found - complete_run_passes,
        "complete_run_pass_rate": pass_rate,
        "declared_test_functions": declared_tests,
        "expected_test_cases": expected_tests,
        "test_case_coverage": test_coverage,
        "status": status,
        "message": message,
        "trials": trials,
    }

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8")

    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        rate_text = "n/a" if pass_rate is None else f"{pass_rate:.0%}"
        lines = [
            "# Difficulty result",
            "",
            f"- Status: **{status}**",
            f"- Complete-run passes: **{complete_run_passes}/{trials_found}** ({rate_text})",
            f"- Complete-run failures: **{trials_found - complete_run_passes}/{trials_found}**",
            f"- Decision: {message}",
            "",
            "## Per-test solvability coverage",
            "",
            "| Test case | Passed trials | Explicit results | Mixed trials |",
            "| --- | ---: | ---: | ---: |",
        ]
        for name in expected_tests:
            coverage = test_coverage[name]
            lines.append(
                f"| `{name}` | {coverage['passes']}/{args.expected} | "
                f"{coverage['trials_with_explicit_result']}/{args.expected} | "
                f"{coverage['mixed_result_trials']} |"
            )

        lines.extend(["", "## Complete trials", ""])
        for index, trial in enumerate(trials, start=1):
            result = "PASS" if trial["complete_run_passed"] else "FAIL"
            lines.append(
                f"- Trial {index}: {result} (reward={trial['reward']}) — `{trial['reward_path']}`"
            )
        args.markdown_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
