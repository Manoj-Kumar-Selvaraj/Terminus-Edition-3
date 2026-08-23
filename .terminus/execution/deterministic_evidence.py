#!/usr/bin/env python3
"""Compile Oracle/NOP empirical evidence into a canonical DETERMINISTIC_VALIDATION StageResult."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


_PYTEST_SUMMARY = re.compile(
    r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S+?)(?:\s+-\s+.*)?$"
)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain one JSON object")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _commit_ref(commit: str) -> dict[str, str]:
    digest = "sha256:" + hashlib.sha256(commit.encode("utf-8")).hexdigest()
    return {"kind": "COMMIT", "ref": f"commit:{commit}", "content_hash": digest}


def _run_ref(run_id: str, evidence: Mapping[str, Any]) -> dict[str, str]:
    digest = "sha256:" + hashlib.sha256(_canonical(evidence)).hexdigest()
    return {
        "kind": "RUN",
        "ref": f"run:github-actions:{run_id}#{digest}",
        "content_hash": digest,
    }


def _test_name(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("test evidence has no usable name")
    name = raw.strip().split("::")[-1]
    return name.split("[", 1)[0]


def _test_status(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("test evidence has no usable status")
    value = raw.strip().lower()
    aliases = {
        "pass": "passed",
        "passed": "passed",
        "success": "passed",
        "fail": "failed",
        "failed": "failed",
        "failure": "failed",
        "error": "error",
        "errored": "error",
        "skip": "skipped",
        "skipped": "skipped",
        "pending": "skipped",
        "xfail": "skipped",
        "xpass": "passed",
    }
    return aliases.get(value, value)


def _tests_from_ctrf(path: Path) -> dict[str, str]:
    payload = _load_object(path, f"CTRF {path}")
    raw_tests: Any = None
    results = payload.get("results")
    if isinstance(results, dict):
        raw_tests = results.get("tests")
    if raw_tests is None:
        raw_tests = payload.get("tests")
    if not isinstance(raw_tests, list) or not raw_tests:
        raise ValueError(f"CTRF {path} has no tests")
    tests: dict[str, str] = {}
    for item in raw_tests:
        if not isinstance(item, dict):
            raise ValueError(f"CTRF {path} contains a non-object test")
        name = _test_name(item.get("name") or item.get("testName") or item.get("id"))
        status = _test_status(item.get("status") or item.get("outcome") or item.get("result"))
        previous = tests.get(name)
        if previous is not None and previous != status:
            raise ValueError(f"CTRF {path} has conflicting statuses for {name}")
        tests[name] = status
    return tests


def _tests_from_pytest_stdout(path: Path) -> dict[str, str]:
    tests: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        match = _PYTEST_SUMMARY.fullmatch(line)
        if match is None:
            continue
        status_raw, nodeid = match.groups()
        name = _test_name(nodeid)
        status = _test_status(status_raw)
        previous = tests.get(name)
        if previous is not None and previous != status:
            raise ValueError(f"pytest stdout {path} has conflicting statuses for {name}")
        tests[name] = status
    if not tests:
        raise ValueError(f"pytest stdout {path} has no explicit test summary records")
    return tests


def _merge_test_reports(
    paths: list[Path],
    label: str,
    loader: Any,
    evidence_kind: str,
) -> tuple[dict[str, str], list[str]]:
    merged: dict[str, str] = {}
    used: list[str] = []
    for path in paths:
        tests = loader(path)
        for name, status in tests.items():
            previous = merged.get(name)
            if previous is not None and previous != status:
                raise ValueError(f"{label} {evidence_kind} evidence conflicts for {name}")
            merged[name] = status
        used.append(str(path))
    if not merged:
        raise ValueError(f"{label} {evidence_kind} evidence contains no tests")
    return merged, used


def _collect_test_evidence(root: Path, label: str) -> tuple[dict[str, str], list[str], str]:
    ctrf_paths = sorted(root.rglob("ctrf.json"))
    if ctrf_paths:
        tests, used = _merge_test_reports(ctrf_paths, label, _tests_from_ctrf, "CTRF")
        return tests, used, "CTRF"

    pytest_paths = sorted(root.rglob("verifier/test-stdout.txt"))
    if pytest_paths:
        tests, used = _merge_test_reports(
            pytest_paths,
            label,
            _tests_from_pytest_stdout,
            "PYTEST_STDOUT",
        )
        return tests, used, "PYTEST_STDOUT"

    raise ValueError(f"{label} produced neither ctrf.json nor verifier/test-stdout.txt")


def _reward(root: Path, label: str) -> float:
    files = sorted(root.rglob("reward.txt"))
    if not files:
        raise ValueError(f"{label} produced no reward.txt")
    values: set[float] = set()
    for path in files:
        raw = path.read_text(encoding="utf-8").strip()
        try:
            values.add(float(raw))
        except ValueError as exc:
            raise ValueError(f"{label} reward is not numeric: {path}") from exc
    if len(values) != 1:
        raise ValueError(f"{label} produced conflicting rewards: {sorted(values)}")
    return next(iter(values))


def _classification(root: Path, task: str, oracle: Mapping[str, str]) -> list[tuple[str, str, str]]:
    map_path = root / ".terminus" / "designs" / f"{task}-test-map.json"
    rows: list[tuple[str, str, str]] = []
    if map_path.is_file():
        payload = _load_object(map_path, "test map")
        raw = payload.get("tests")
        if not isinstance(raw, list) or not raw:
            raise ValueError("test map has no classified tests")
        for item in raw:
            if not isinstance(item, list) or len(item) < 2:
                raise ValueError("test map row is invalid")
            name = str(item[0])
            category = str(item[1]).upper()
            requirement = str(item[2]) if len(item) > 2 else ""
            if category not in {"F2P", "P2P"}:
                raise ValueError(f"test map has unsupported classification {category}")
            rows.append((name, category, requirement))
    else:
        for name in sorted(oracle):
            if name.startswith("test_f2p_"):
                rows.append((name, "F2P", ""))
            elif name.startswith("test_p2p_"):
                rows.append((name, "P2P", ""))
    if not rows:
        raise ValueError("no F2P/P2P classification is available")
    if len({name for name, _category, _req in rows}) != len(rows):
        raise ValueError("F2P/P2P classification contains duplicate tests")
    if not any(category == "F2P" for _name, category, _req in rows):
        raise ValueError("F2P classification is empty")
    if not any(category == "P2P" for _name, category, _req in rows):
        raise ValueError("P2P classification is empty")
    return rows


def compile_result(
    root: Path,
    *,
    request: Mapping[str, Any],
    invocation: Mapping[str, Any],
    oracle_root: Path,
    nop_root: Path,
    run_id: str,
    run_attempt: str,
) -> dict[str, Any]:
    if request.get("stage_id") != "DETERMINISTIC_VALIDATION":
        raise ValueError("request is not DETERMINISTIC_VALIDATION")
    if invocation.get("invocation_id") != request.get("invocation_id"):
        raise ValueError("deterministic evidence invocation_id mismatch")
    stage = invocation.get("stage")
    if not isinstance(stage, dict) or stage.get("stage_id") != "DETERMINISTIC_VALIDATION":
        raise ValueError("invocation is not DETERMINISTIC_VALIDATION")
    if stage.get("role_class") != "CONTROLLER" or stage.get("role_id") != "CREATION_CONTROLLER":
        raise ValueError("deterministic invocation has unexpected controller authority")

    task = request.get("task_id")
    task_commit = request.get("task_commit")
    control_commit = request.get("control_plane_commit")
    if not all(isinstance(value, str) and value for value in (task, task_commit, control_commit)):
        raise ValueError("deterministic request identity is incomplete")

    oracle_reward = _reward(oracle_root, "Oracle")
    nop_reward = _reward(nop_root, "NOP")
    oracle_tests, oracle_reports, oracle_report_kind = _collect_test_evidence(oracle_root, "Oracle")
    nop_tests, nop_reports, nop_report_kind = _collect_test_evidence(nop_root, "NOP")
    rows = _classification(root, task, oracle_tests)

    f2p: list[dict[str, Any]] = []
    p2p: list[dict[str, Any]] = []
    oracle_failures: list[str] = []
    classification_failures: list[str] = []
    for name, category, requirement in rows:
        if name not in oracle_tests:
            raise ValueError(f"Oracle test evidence is missing classified test {name}")
        if name not in nop_tests:
            raise ValueError(f"NOP test evidence is missing classified test {name}")
        oracle_status = oracle_tests[name]
        nop_status = nop_tests[name]
        if oracle_status != "passed":
            oracle_failures.append(f"{name}: oracle={oracle_status}")
        expected_nop = "failed" if category == "F2P" else "passed"
        if nop_status != expected_nop:
            classification_failures.append(
                f"{name}: class={category} nop={nop_status} expected={expected_nop}"
            )
        item = {
            "test": name,
            "requirement": requirement,
            "oracle_status": oracle_status,
            "nop_status": nop_status,
            "expected_nop_status": expected_nop,
        }
        (f2p if category == "F2P" else p2p).append(item)

    evidence_summary = {
        "request_id": request.get("request_id"),
        "invocation_id": request.get("invocation_id"),
        "task_id": task,
        "task_commit": task_commit,
        "control_plane_commit": control_commit,
        "workflow_run_id": str(run_id),
        "workflow_run_attempt": str(run_attempt),
        "oracle_reward": oracle_reward,
        "nop_reward": nop_reward,
        "oracle_test_report_kind": oracle_report_kind,
        "nop_test_report_kind": nop_report_kind,
        "oracle_test_reports": oracle_reports,
        "nop_test_reports": nop_reports,
        "f2p_count": len(f2p),
        "p2p_count": len(p2p),
    }
    refs = [
        _commit_ref(task_commit),
        _commit_ref(control_commit),
        _run_ref(str(run_id), evidence_summary),
    ]

    pass_reward = oracle_reward == 1.0 and nop_reward == 0.0
    if pass_reward and not oracle_failures and not classification_failures:
        return {
            "schema_version": "1.0",
            "invocation_id": request["invocation_id"],
            "output_task_commit": task_commit,
            "status": "PASS",
            "outputs": {
                "ORACLE_REWARD": 1,
                "NOP_REWARD": 0,
                "F2P_EMPIRICAL_MATRIX": f2p,
                "P2P_EMPIRICAL_MATRIX": p2p,
            },
            "evidence_refs": refs,
        }

    if oracle_reward != 1.0 or oracle_failures:
        route_key = "RUNTIME_OR_ORACLE_FAILURE"
        failure_class = "ORACLE_OR_RUNTIME_FAILURE"
        meaningful = oracle_failures[0] if oracle_failures else f"Oracle reward={oracle_reward}"
    else:
        route_key = "VERIFIER_CONTRACT_FAILURE"
        failure_class = "VERIFIER_EMPIRICAL_CLASSIFICATION_FAILURE"
        meaningful = (
            classification_failures[0]
            if classification_failures
            else f"NOP reward={nop_reward} expected=0"
        )
    return {
        "schema_version": "1.0",
        "invocation_id": request["invocation_id"],
        "output_task_commit": task_commit,
        "status": "FAIL",
        "outputs": {
            "FAILURE_CLASS": failure_class,
            "FIRST_MEANINGFUL_ERROR": meaningful,
        },
        "evidence_refs": refs,
        "route_key": route_key,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--request", required=True)
    parser.add_argument("--invocation", required=True)
    parser.add_argument("--oracle-root", required=True)
    parser.add_argument("--nop-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    result = compile_result(
        root,
        request=_load_object(Path(args.request), "request"),
        invocation=_load_object(Path(args.invocation), "invocation"),
        oracle_root=Path(args.oracle_root),
        nop_root=Path(args.nop_root),
        run_id=args.run_id,
        run_attempt=args.run_attempt,
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
