from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.deterministic_evidence import compile_result  # noqa: E402

TASK = "terraform-ansible-managed-resources"
INVOCATION_ID = "inv_" + "c" * 64


def _request() -> dict[str, object]:
    return {
        "request_id": "detreq_" + "d" * 64,
        "stage_id": "DETERMINISTIC_VALIDATION",
        "task_id": TASK,
        "task_commit": "a" * 40,
        "control_plane_commit": "b" * 40,
        "invocation_id": INVOCATION_ID,
    }


def _invocation() -> dict[str, object]:
    return {
        "invocation_id": INVOCATION_ID,
        "stage": {
            "stage_id": "DETERMINISTIC_VALIDATION",
            "role_class": "CONTROLLER",
            "role_id": "CREATION_CONTROLLER",
        },
    }


def _write_pytest_stdout(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["=========================== short test summary info ============================"]
    for name, status in rows:
        if status == "passed":
            lines.append(f"PASSED ../../tests/test_outputs.py::{name}")
        elif status == "failed":
            lines.append(f"FAILED ../../tests/test_outputs.py::{name} - AssertionError: expected failure")
        else:
            lines.append(f"{status.upper()} ../../tests/test_outputs.py::{name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    test_map = json.loads(
        (ROOT / ".terminus" / "designs" / f"{TASK}-test-map.json").read_text(
            encoding="utf-8"
        )
    )
    oracle_rows: list[tuple[str, str]] = []
    nop_rows: list[tuple[str, str]] = []
    for name, category, _requirement in test_map["tests"]:
        oracle_rows.append((name, "passed"))
        nop_rows.append((name, "failed" if category == "F2P" else "passed"))

    oracle = tmp_path / "oracle"
    nop = tmp_path / "nop"
    _write_pytest_stdout(oracle / "trial" / "verifier" / "test-stdout.txt", oracle_rows)
    _write_pytest_stdout(nop / "trial" / "verifier" / "test-stdout.txt", nop_rows)
    (oracle / "trial" / "verifier" / "reward.txt").write_text("1\n", encoding="utf-8")
    (nop / "trial" / "verifier" / "reward.txt").write_text("0\n", encoding="utf-8")
    return oracle, nop


def test_compiler_accepts_current_harbor_pytest_stdout_layout(tmp_path: Path) -> None:
    oracle, nop = _fixture(tmp_path)
    result = compile_result(
        ROOT,
        request=_request(),
        invocation=_invocation(),
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


def test_compiler_does_not_infer_tests_from_reward_only(tmp_path: Path) -> None:
    oracle = tmp_path / "oracle"
    nop = tmp_path / "nop"
    oracle.mkdir()
    nop.mkdir()
    (oracle / "reward.txt").write_text("1\n", encoding="utf-8")
    (nop / "reward.txt").write_text("0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="neither ctrf.json nor verifier/test-stdout.txt"):
        compile_result(
            ROOT,
            request=_request(),
            invocation=_invocation(),
            oracle_root=oracle,
            nop_root=nop,
            run_id="12345",
            run_attempt="1",
        )
