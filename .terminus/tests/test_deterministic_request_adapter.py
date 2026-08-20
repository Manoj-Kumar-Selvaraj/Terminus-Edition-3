from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.deterministic_evidence import compile_result  # noqa: E402
from execution.deterministic_request import (  # noqa: E402
    STAGE_ID,
    build_request,
    dispatch_envelope,
    validate_request,
)

TASK = "terraform-ansible-managed-resources"
INVOCATION_ID = "inv_" + "a" * 64
INPUTS = {
    "CURRENT_TASK_COMMIT": {"status": "CURRENT"},
    "ORACLE": {"status": "CURRENT"},
    "STARTER_NOP_STATE": {"status": "CURRENT"},
    "VERIFIER": {"F2P_COUNT": 30, "P2P_COUNT": 6},
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _task_commit() -> str:
    return _git("log", "-1", "--format=%H", "--", TASK)


def _request() -> dict[str, object]:
    head = _git("rev-parse", "HEAD")
    return build_request(
        ROOT,
        task_id=TASK,
        task_commit=_task_commit(),
        control_plane_commit=head,
        invocation_id=INVOCATION_ID,
        inputs=INPUTS,
        expected_repository_head=head,
    )


def test_request_is_deterministic_invocation_and_commit_bound() -> None:
    request = _request()
    second = _request()
    head = _git("rev-parse", "HEAD")
    task_commit = _task_commit()
    assert request == second
    assert request["schema_version"] == "1.1"
    assert request["request_id"].startswith("detreq_")
    assert request["stage_id"] == STAGE_ID
    assert request["task_commit"] == task_commit
    assert request["expected_repository_head"] == head
    assert request["invocation_id"] == INVOCATION_ID
    assert request["inputs"] == INPUTS
    assert request["evidence_contract"] == {
        "oracle_reward": 1,
        "nop_reward": 0,
        "require_f2p_empirical_matrix": True,
        "require_p2p_empirical_matrix": True,
    }

    validated = validate_request(ROOT, request, request_base=head)
    assert validated["request_id"] == request["request_id"]
    assert validated["invocation_id"] == INVOCATION_ID
    assert validated["inputs"] == INPUTS
    assert validated["task_id"] == TASK
    assert validated["task_commit"] == task_commit


def test_request_rejects_branch_contract_and_invocation_drift() -> None:
    head = _git("rev-parse", "HEAD")
    parent = _git("rev-parse", "HEAD^")
    request = _request()
    with pytest.raises(ValueError, match="branch/base mismatch"):
        validate_request(ROOT, request, request_base=parent)

    drifted = json.loads(json.dumps(request))
    drifted["evidence_contract"]["oracle_reward"] = 0
    with pytest.raises(ValueError, match="evidence contract drift"):
        validate_request(ROOT, drifted, request_base=head)

    drifted = json.loads(json.dumps(request))
    drifted["invocation_id"] = "inv_" + "b" * 64
    with pytest.raises(ValueError, match="request_id is invalid"):
        validate_request(ROOT, drifted, request_base=head)


def test_dispatch_envelope_uses_repository_write_trigger_and_locator() -> None:
    request = _request()
    dispatch = dispatch_envelope(request)
    assert dispatch["status"] == "READY_TO_DISPATCH"
    assert dispatch["execution_mode"] == "HOSTED_DETERMINISTIC_VALIDATION"
    assert dispatch["workflow"] == ".github/workflows/terminus-deterministic-request.yml"
    assert dispatch["trigger"] == "REQUEST_BRANCH_PUSH"
    assert dispatch["branch"].startswith(f"terminus-deterministic-request/{TASK}/")
    assert dispatch["request_path"].startswith(".terminus/deterministic-requests/")
    assert dispatch["run_locator"] == ".terminus/deterministic-run-locators/<task>/<request-commit>.json"
    assert dispatch["request"] == request


def _write_ctrf(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "results": {
                    "tests": [
                        {"name": name, "status": status}
                        for name, status in rows
                    ]
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _empirical_fixture(tmp_path: Path, *, break_f2p: bool = False) -> tuple[Path, Path]:
    test_map = json.loads(
        (ROOT / ".terminus" / "designs" / f"{TASK}-test-map.json").read_text(
            encoding="utf-8"
        )
    )
    oracle_rows: list[tuple[str, str]] = []
    nop_rows: list[tuple[str, str]] = []
    changed = False
    for name, category, _requirement in test_map["tests"]:
        oracle_rows.append((name, "passed"))
        status = "failed" if category == "F2P" else "passed"
        if break_f2p and category == "F2P" and not changed:
            status = "passed"
            changed = True
        nop_rows.append((name, status))
    oracle = tmp_path / "oracle"
    nop = tmp_path / "nop"
    _write_ctrf(oracle / "ctrf.json", oracle_rows)
    _write_ctrf(nop / "ctrf.json", nop_rows)
    (oracle / "reward.txt").write_text("1\n", encoding="utf-8")
    (nop / "reward.txt").write_text("0\n", encoding="utf-8")
    return oracle, nop


def _minimal_invocation() -> dict[str, object]:
    return {
        "invocation_id": INVOCATION_ID,
        "stage": {
            "stage_id": "DETERMINISTIC_VALIDATION",
            "role_class": "CONTROLLER",
            "role_id": "CREATION_CONTROLLER",
        },
    }


def test_empirical_compiler_builds_real_f2p_p2p_stage_result(tmp_path: Path) -> None:
    oracle, nop = _empirical_fixture(tmp_path)
    result = compile_result(
        ROOT,
        request=_request(),
        invocation=_minimal_invocation(),
        oracle_root=oracle,
        nop_root=nop,
        run_id="12345",
        run_attempt="1",
    )
    assert result["status"] == "PASS"
    outputs = result["outputs"]
    assert outputs["ORACLE_REWARD"] == 1
    assert outputs["NOP_REWARD"] == 0
    assert len(outputs["F2P_EMPIRICAL_MATRIX"]) == 30
    assert len(outputs["P2P_EMPIRICAL_MATRIX"]) == 6
    assert all(row["oracle_status"] == "passed" for row in outputs["F2P_EMPIRICAL_MATRIX"])
    assert all(row["nop_status"] == "failed" for row in outputs["F2P_EMPIRICAL_MATRIX"])
    assert all(row["nop_status"] == "passed" for row in outputs["P2P_EMPIRICAL_MATRIX"])
    assert any(ref["kind"] == "RUN" for ref in result["evidence_refs"])


def test_empirical_compiler_routes_nop_classification_failure_to_verifier(tmp_path: Path) -> None:
    oracle, nop = _empirical_fixture(tmp_path, break_f2p=True)
    result = compile_result(
        ROOT,
        request=_request(),
        invocation=_minimal_invocation(),
        oracle_root=oracle,
        nop_root=nop,
        run_id="12345",
        run_attempt="1",
    )
    assert result["status"] == "FAIL"
    assert result["route_key"] == "VERIFIER_CONTRACT_FAILURE"
    assert result["outputs"]["FAILURE_CLASS"] == "VERIFIER_EMPIRICAL_CLASSIFICATION_FAILURE"


def test_controller_and_workflow_own_full_deterministic_transport() -> None:
    controller = (ROOT / ".terminus/execution/controller_cli.py").read_text(encoding="utf-8")
    for marker in (
        "build_deterministic_request",
        "deterministic_dispatch_envelope",
        'stage_id == "DETERMINISTIC_VALIDATION"',
        '"HOSTED_DETERMINISTIC_VALIDATION"',
        "expected_repository_head=_git_head(root)",
    ):
        assert marker in controller

    workflow = (ROOT / ".github/workflows/terminus-deterministic-request.yml").read_text(
        encoding="utf-8"
    )
    for marker in (
        "terminus-deterministic-request/**",
        ".terminus/deterministic-requests/*.json",
        "deterministic_request.py validate",
        "Reconstruct exact controller invocation",
        "HOSTED_DETERMINISTIC_VALIDATION",
        "Execute Oracle evidence",
        "terminus3.sh oracle",
        "Execute NOP evidence",
        "terminus3.sh nop",
        "deterministic_evidence.py",
        "Compile empirical StageResult",
        "controller_cli.py record",
        "Record deterministic result on canonical main",
        "Main changed in deterministic task scope",
        "Control plane changed before deterministic recording",
        "evidence-binding.json",
        "Upload deterministic evidence",
    ):
        assert marker in workflow
    assert "contents: write" in workflow
    for forbidden in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CURSOR_API_KEY",
        "STB_AI_API_KEY",
        "terminus-quality-executor.yml",
    ):
        assert forbidden not in workflow


def test_deterministic_run_locator_makes_push_runs_pollable() -> None:
    workflow = (ROOT / ".github/workflows/terminus-deterministic-run-locator.yml").read_text(
        encoding="utf-8"
    )
    for marker in (
        'workflows: ["Terminus Deterministic Request"]',
        "types: [requested, in_progress, completed]",
        "terminus-deterministic-request/",
        ".terminus/deterministic-requests/*.json",
        ".terminus/deterministic-run-locators/$task/$REQUEST_SHA.json",
        "DETERMINISTIC_RUN",
        "Deterministic validation request",
        "run_id",
        "job_id",
        "git push origin \"HEAD:$REQUEST_BRANCH\"",
    ):
        assert marker in workflow
    assert "contents: write" in workflow
    assert "actions: read" in workflow
