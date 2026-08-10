"""Behavioral checks for the SKU tape COMP-3 unpacker."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path("/app/equiv")
BIN = ROOT / "bin" / "equiv-eval"
REPORT = ROOT / "out" / "equivalence-report.json"
LAYOUT = ROOT / "programs" / "skumast.layout"
PUBLIC = ROOT / "samples" / "sku-public.dat"
HOLD_HEX = Path("/tests/fixtures/holdout.hex")


def _run(args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    cmd = [str(BIN)]
    if args:
        cmd.extend(args)
    return subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True, check=False)


def _report() -> dict:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def _holdout_bytes() -> bytes:
    hex_chars = []
    for line in HOLD_HEX.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        hex_chars.append(stripped)
    return bytes.fromhex("".join(hex_chars))


def test_f2p_public_positive_comp3_qoh():
    """Public record 0 unpacks signed positive COMP-3 QOH with implied decimal scale."""
    rec = _report()["records"][0]["fields"]
    assert rec["QOH"] == "1234.56"


def test_f2p_public_unit_cost_scale_three():
    """Public UNIT-COST keeps three implied decimal places."""
    assert _report()["records"][0]["fields"]["UNIT-COST"] == "12.500"


def test_f2p_public_first_record_byte_length():
    """ODO count 1 yields prefix plus one 16-byte bin occurrence."""
    rec = _report()["records"][0]
    assert rec["byte_length"] == 44
    assert rec["fields"]["BIN-COUNT"] == 1
    assert len(rec["fields"]["BIN-ENTRY"]) == 1
    assert rec["fields"]["BIN-ENTRY"][0]["WHSE"] == "W001"
    assert rec["fields"]["BIN-ENTRY"][0]["AISLE"] == 12
    assert rec["fields"]["BIN-ENTRY"][0]["QTY-IN-BIN"] == "5"


def test_f2p_public_negative_qoh_sign_d():
    """Public record 1 unpacks a D-nibble negative QOH."""
    rec = _report()["records"][1]["fields"]
    assert rec["QOH"] == "-42.10"
    assert rec["BIN-COUNT"] == 0
    assert rec["BIN-ENTRY"] == []


def test_f2p_public_zero_odo_byte_length():
    """BIN-COUNT 0 must not consume the max OCCURS span."""
    assert _report()["records"][1]["byte_length"] == 28
    assert sum(rec["byte_length"] for rec in _report()["records"]) == PUBLIC.stat().st_size


def test_f2p_redefines_shares_status_byte():
    """REDEFINES ACTIVE-FLAG occupies the same byte as STATUS-BYTE."""
    rec = _report()["records"][0]["fields"]
    assert rec["STATUS-BYTE"] == rec["ACTIVE-FLAG"] == "A"
    rec2 = _report()["records"][1]["fields"]
    assert rec2["STATUS-BYTE"] == rec2["ACTIVE-FLAG"] == "I"


def test_f2p_unsigned_reorder_sign_f():
    """Unsigned COMP-3 REORDER-PT with sign nibble F unpacks as a decimal string."""
    assert _report()["records"][0]["fields"]["REORDER-PT"] == "25"


def test_f2p_summary_flags_true_on_public_tape():
    """Public evaluation summary reports signed, ODO, and REDEFINES success."""
    summary = _report()["summary"]
    assert summary["record_count"] == 2
    assert summary["error_count"] == 0
    assert summary["comp3_signed_ok"] is True
    assert summary["odo_lengths_ok"] is True
    assert summary["redefines_ok"] is True
    assert _report()["layout_id"] == "SKU-REC"


def test_f2p_unknown_flag_exits_without_clobber():
    """Unknown flags exit 2 and leave the existing report in place."""
    before = REPORT.read_bytes()
    cp = _run(["--nope"])
    assert cp.returncode == 2
    assert REPORT.read_bytes() == before


def test_f2p_holdout_negative_packed_fields():
    """Hidden tape unpacks negative QOH and UNIT-COST from sealed bytes."""
    target = Path("/tmp/holdout.dat")
    out = Path("/tmp/holdout-report.json")
    target.write_bytes(_holdout_bytes())
    cp = _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    assert cp.returncode == 0, cp.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    rec = data["records"][0]["fields"]
    assert rec["QOH"] == "-100.05"
    assert rec["UNIT-COST"] == "-0.125"


def test_f2p_holdout_unsigned_reorder_max():
    """Hidden tape unpacks unsigned COMP-3 99999 with sign F."""
    target = Path("/tmp/holdout.dat")
    out = Path("/tmp/holdout-report.json")
    target.write_bytes(_holdout_bytes())
    _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    rec = json.loads(out.read_text(encoding="utf-8"))["records"][0]["fields"]
    assert rec["REORDER-PT"] == "99999"


def test_f2p_holdout_odo_two_bins_mixed_signs():
    """Hidden ODO count 2 yields two bins and mixed signed packed quantities."""
    target = Path("/tmp/holdout.dat")
    out = Path("/tmp/holdout-report.json")
    target.write_bytes(_holdout_bytes())
    _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    rec = json.loads(out.read_text(encoding="utf-8"))["records"][0]
    assert rec["fields"]["BIN-COUNT"] == 2
    assert len(rec["fields"]["BIN-ENTRY"]) == 2
    assert rec["fields"]["BIN-ENTRY"][0]["QTY-IN-BIN"] == "-12"
    assert rec["fields"]["BIN-ENTRY"][1]["QTY-IN-BIN"] == "7"
    assert rec["byte_length"] == 28 + 32


def test_f2p_holdout_second_record_zero_odo():
    """Second hidden record with BIN-COUNT 0 starts immediately after the short first record."""
    target = Path("/tmp/holdout.dat")
    out = Path("/tmp/holdout-report.json")
    target.write_bytes(_holdout_bytes())
    cp = _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    assert cp.returncode == 0, cp.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["records"]) == 2
    rec = data["records"][1]["fields"]
    assert rec["SKU-CODE"] == "SKU-HOLD0002"
    assert rec["QOH"] == "0.01"
    assert rec["BIN-COUNT"] == 0
    assert rec["BIN-ENTRY"] == []
    assert data["records"][1]["byte_length"] == 28
    assert sum(item["byte_length"] for item in data["records"]) == target.stat().st_size


def test_f2p_holdout_redefines_status():
    """Hidden STATUS-BYTE Z is also exposed through the REDEFINES name."""
    target = Path("/tmp/holdout.dat")
    out = Path("/tmp/holdout-report.json")
    target.write_bytes(_holdout_bytes())
    _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    rec = json.loads(out.read_text(encoding="utf-8"))["records"][0]["fields"]
    assert rec["STATUS-BYTE"] == rec["ACTIVE-FLAG"] == "Z"


def test_f2p_display_fields_keep_pic_padding():
    """PIC X fields keep trailing spaces; scale-0 COMP-3 has no dummy fractional part."""
    rec = _report()["records"][0]["fields"]
    assert rec["BIN-ENTRY"][0]["SLOT"] == "A10   "
    assert rec["BIN-ENTRY"][0]["QTY-IN-BIN"] == "5"
    assert "." not in rec["BIN-ENTRY"][0]["QTY-IN-BIN"]


def test_f2p_cli_default_writes_contract_path():
    """Default equiv-eval invocation writes the contracted report path."""
    assert REPORT.is_file()
    assert _report()["source_records"].endswith("sku-public.dat")


def test_p2p_layout_and_sample_retained():
    """Public layout program and sample tape remain available."""
    assert LAYOUT.is_file()
    assert PUBLIC.is_file()
    assert PUBLIC.stat().st_size == 72


def _fixture_bytes(name: str) -> bytes:
    hex_chars = []
    for line in Path(f"/tests/fixtures/{name}").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        hex_chars.append(stripped)
    return bytes.fromhex("".join(hex_chars))


def test_f2p_invalid_sign_nibble_is_record_error():
    """A non C/D/F packed sign nibble becomes a record error and fails signed summary."""
    target = Path("/tmp/invalid-sign.dat")
    out = Path("/tmp/invalid-sign-report.json")
    target.write_bytes(_fixture_bytes("invalid-sign.hex"))
    cp = _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    assert cp.returncode == 1, cp.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["records"][0]["error"]
    assert "sign" in data["records"][0]["error"].lower()
    assert data["summary"]["comp3_signed_ok"] is False
    assert data["summary"]["error_count"] >= 1


def test_f2p_invalid_odo_count_is_record_error():
    """BIN-COUNT outside the OCCURS bounds is a record error and fails ODO summary."""
    target = Path("/tmp/invalid-odo.dat")
    out = Path("/tmp/invalid-odo-report.json")
    target.write_bytes(_fixture_bytes("invalid-odo.hex"))
    cp = _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    assert cp.returncode == 1, cp.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["records"][0]["error"]
    assert "odo" in data["records"][0]["error"].lower()
    assert data["summary"]["odo_lengths_ok"] is False
    assert data["summary"]["error_count"] >= 1


def test_f2p_rerun_is_byte_identical():
    """A second default equiv-eval run rewrites the same report bytes."""
    before = REPORT.read_bytes()
    cp = _run()
    assert cp.returncode == 0, cp.stderr
    assert REPORT.read_bytes() == before


def test_p2p_incident_evidence_present():
    """Public handoff and incident log remain on the submitted tree."""
    assert (ROOT / "ops" / "handoff.md").is_file()
    assert (ROOT / "log" / "unpack-incident.log").is_file()
    assert (ROOT / "docs" / "record-layout.md").is_file()
