"""Behavioral verifier for the fluid dynamics analysis workbench."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path("/app/fluidlab")
BIN = ROOT / "bin" / "fluidlab"
RUN_SCRIPT = ROOT / "scripts" / "run_analysis.sh"
BUILD_SCRIPT = ROOT / "scripts" / "build.sh"
OUT = ROOT / "output"
SUMMARY = OUT / "summary.json"
CSV = OUT / "operating_points.csv"
CHECKPOINT = OUT / "checkpoints" / "current.json"
CONFIG = ROOT / "config" / "system.json"
GOLDEN = Path("/tests/fixtures/golden")
SUMMARY_TOP_LEVEL = [
    "schema_version",
    "system_name",
    "publication_revision",
    "status",
    "fleet_rollup",
    "cases",
]
FLEET_ROLLUP_KEYS = {
    "case_count",
    "operating_point_count",
    "status_counts",
    "worst_mach_margin",
    "worst_cfl_margin",
    "worst_pressure_margin_pa",
    "worst_temperature_margin_k",
    "worst_mesh_score",
}


def run_analyze(*, use_script: bool = False) -> subprocess.CompletedProcess[str]:
    """Run the shared analysis entrypoint against the workbench root."""
    if use_script:
        completed = subprocess.run(
            ["bash", str(RUN_SCRIPT)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    else:
        completed = subprocess.run(
            ["bash", str(BIN), "analyze", "--root", str(ROOT)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    if completed.returncode != 0:
        pytest.fail(
            f"analysis failed rc={completed.returncode}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed


def clear_output() -> None:
    """Remove prior publication artifacts before a fresh analysis run."""
    shutil.rmtree(OUT, ignore_errors=True)


def load_summary() -> dict[str, object]:
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def load_csv_rows() -> list[dict[str, str]]:
    with CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_checkpoint() -> dict[str, object]:
    return json.loads(CHECKPOINT.read_text(encoding="utf-8"))


def point_lookup(summary: dict[str, object], case_id: str, point_id: str) -> dict[str, object]:
    for case in summary["cases"]:
        if case["case_id"] != case_id:
            continue
        for point in case["operating_points"]:
            if point["point_id"] == point_id:
                return point
    raise AssertionError(f"missing operating point {case_id}/{point_id}")


@pytest.fixture(scope="session", autouse=True)
def published_analysis() -> None:
    """Publish one deterministic fleet report before behavioral checks."""
    clear_output()
    run_analyze()


def test_f2p_build_and_entrypoints_exist() -> None:
    """The inherited build script and shared CLI wrappers must remain available."""
    assert BUILD_SCRIPT.is_file()
    assert BIN.is_file()
    assert RUN_SCRIPT.is_file()
    subprocess.run(["bash", str(BUILD_SCRIPT)], cwd=str(ROOT), check=True, timeout=60)


def test_f2p_run_script_publishes_same_artifacts() -> None:
    """The run_analysis wrapper must publish the same artifact set as the CLI."""
    clear_output()
    run_analyze(use_script=True)
    assert SUMMARY.is_file()
    assert CSV.is_file()
    assert CHECKPOINT.is_file()


def test_f2p_summary_contract_shape_and_field_order() -> None:
    """summary.json must follow the documented top-level field order and fleet rollup keys."""
    summary = load_summary()
    assert list(summary.keys()) == SUMMARY_TOP_LEVEL
    assert summary["schema_version"] == "1.0"
    assert summary["system_name"] == "fluidlab"
    rollup = summary["fleet_rollup"]
    assert set(rollup.keys()) == FLEET_ROLLUP_KEYS
    assert list(rollup["status_counts"].keys()) == ["FAIL", "WARN", "PASS"]


def test_f2p_publication_revision_and_golden_digest() -> None:
    """Publication revision must match the deterministic golden reference run."""
    golden = json.loads((GOLDEN / "summary.json").read_text(encoding="utf-8"))
    summary = load_summary()
    assert summary["publication_revision"] == golden["publication_revision"]


def test_f2p_fleet_status_is_fail_with_single_limit_violation() -> None:
    """Fleet status must reflect the one failing compressible overdrive point."""
    summary = load_summary()
    assert summary["status"] == "FAIL"
    counts = summary["fleet_rollup"]["status_counts"]
    assert counts == {"FAIL": 1, "WARN": 0, "PASS": 7}


def test_f2p_cases_sorted_and_case_statuses() -> None:
    """Cases must publish in case_id order with nozzle-array failing on overdrive."""
    summary = load_summary()
    case_ids = [case["case_id"] for case in summary["cases"]]
    assert case_ids == ["manifold-balance", "nozzle-array", "thermal-loop"]
    statuses = {case["case_id"]: case["status"] for case in summary["cases"]}
    assert statuses == {
        "manifold-balance": "PASS",
        "nozzle-array": "FAIL",
        "thermal-loop": "PASS",
    }


def test_f2p_qualified_run_passes_compressible_envelope() -> None:
    """The qualified nozzle operating point must stay inside the pressure envelope."""
    point = point_lookup(load_summary(), "nozzle-array", "qualified-run")
    assert point["status"] == "PASS"
    assert point["findings"] == []
    assert point["margins"]["pressure_margin_pa"] > 0.0


def test_f2p_overdrive_reports_pressure_drop_limit() -> None:
    """The overdrive nozzle point must fail on pressure drop with one explicit finding."""
    point = point_lookup(load_summary(), "nozzle-array", "overdrive")
    assert point["status"] == "FAIL"
    assert len(point["findings"]) == 1
    finding = point["findings"][0]
    assert finding["code"] == "PRESSURE_DROP_LIMIT"
    assert finding["severity"] == "FAIL"
    assert point["margins"]["pressure_margin_pa"] < 0.0


def test_f2p_csv_columns_order_and_severity_sort() -> None:
    """CSV rows must use configured columns and severity-first ordering within each case."""
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = load_csv_rows()
    assert rows
    assert list(rows[0].keys()) == config["csv_fields"]
    golden_rows = (GOLDEN / "operating_points.csv").read_text(encoding="utf-8").splitlines()
    assert CSV.read_text(encoding="utf-8").splitlines() == golden_rows


def test_f2p_checkpoint_matches_summary_state() -> None:
    """Checkpoint status, revision, and per-case digests must mirror summary.json."""
    summary = load_summary()
    checkpoint = load_checkpoint()
    golden_checkpoint = json.loads((GOLDEN / "current.json").read_text(encoding="utf-8"))
    assert checkpoint["publication_revision"] == summary["publication_revision"]
    assert checkpoint["status"] == summary["status"]
    assert checkpoint["cases"] == golden_checkpoint["cases"]
    artifact_paths = [entry["path"] for entry in checkpoint["artifacts"]]
    assert artifact_paths == [
        "/app/fluidlab/output/summary.json",
        "/app/fluidlab/output/operating_points.csv",
        "/app/fluidlab/output/checkpoints/current.json",
    ]


def test_f2p_all_operating_points_preserve_lineage() -> None:
    """Every configured operating point must appear once across JSON and CSV outputs."""
    summary = load_summary()
    csv_rows = load_csv_rows()
    assert len(csv_rows) == summary["fleet_rollup"]["operating_point_count"] == 8
    json_keys = {
        (case["case_id"], point["point_id"])
        for case in summary["cases"]
        for point in case["operating_points"]
    }
    csv_keys = {(row["case_id"], row["point_id"]) for row in csv_rows}
    assert json_keys == csv_keys


def test_f2p_summary_bytes_match_golden_reference() -> None:
    """The published summary must byte-match the golden deterministic reference artifact."""
    golden_bytes = (GOLDEN / "summary.json").read_bytes()
    assert SUMMARY.read_bytes() == golden_bytes


def test_f2p_deterministic_rerun_produces_identical_summary() -> None:
    """Repeated analysis runs must emit identical summary bytes."""
    first = SUMMARY.read_bytes()
    run_analyze()
    second = SUMMARY.read_bytes()
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_p2p_liquid_cases_remain_pass() -> None:
    """Liquid manifold and thermal cases must publish PASS for every operating point."""
    summary = load_summary()
    for case_id in ("manifold-balance", "thermal-loop"):
        case = next(item for item in summary["cases"] if item["case_id"] == case_id)
        assert case["status"] == "PASS"
        assert all(point["status"] == "PASS" for point in case["operating_points"])
