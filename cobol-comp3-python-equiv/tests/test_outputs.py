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


def test_f2p_summary_fields_on_public_tape():
    """Public evaluation summary reports record/error counts and signed COMP-3 success."""
    summary = _report()["summary"]
    assert summary["record_count"] == 2
    assert summary["error_count"] == 0
    assert summary["comp3_signed_ok"] is True
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
    """Default equiv-eval invocation writes the contracted report path and source path."""
    assert REPORT.is_file()
    assert _report()["source_records"] == str(PUBLIC)


def test_f2p_layout_override_is_honored():
    """--layout controls actual field binding, widths, types, and record length."""
    custom_layout = Path("/tmp/semantic-override.layout")
    target = Path("/tmp/semantic-override.dat")
    out = Path("/tmp/semantic-override-report.json")
    custom_layout.write_text(
        "\n".join(
            [
                "LAYOUT ALT-SEMANTIC",
                "FIELD CODE PIC X(4)",
                "FIELD COUNT PIC 9(2)",
                "FIELD VALUE PIC S9(3)V9 COMP-3",
                "END",
                "",
            ]
        ),
        encoding="utf-8",
    )
    target.write_bytes(b"ABCD07" + bytes((0x01, 0x23, 0x4C)))
    cp = _run(
        ["--layout", str(custom_layout), "--records", str(target), "--out", str(out)]
    )
    assert cp.returncode == 0, cp.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["layout_id"] == "ALT-SEMANTIC"
    assert data["source_records"] == str(target)
    assert len(data["records"]) == 1
    record = data["records"][0]
    assert record["byte_length"] == 9
    assert record["error"] is None
    assert record["fields"] == {"CODE": "ABCD", "COUNT": 7, "VALUE": "123.4"}


def test_f2p_report_schema_required_fields():
    """Successful reports expose the documented stable record and summary fields/types."""
    data = _report()
    assert data["layout_id"] == "SKU-REC"
    assert data["source_records"] == str(PUBLIC)
    assert [record["index"] for record in data["records"]] == [0, 1]
    for record in data["records"]:
        assert isinstance(record["index"], int)
        assert isinstance(record["byte_length"], int)
        assert record["error"] is None
        assert isinstance(record["fields"], dict)
    summary = data["summary"]
    assert isinstance(summary["record_count"], int)
    assert isinstance(summary["error_count"], int)
    assert isinstance(summary["comp3_signed_ok"], bool)


def test_f2p_indeterminate_record_length_reports_zero():
    """A truncated record with no determinable boundary reports byte_length 0 and an error."""
    target = Path("/tmp/truncated.dat")
    out = Path("/tmp/truncated-report.json")
    target.write_bytes(PUBLIC.read_bytes()[:10])
    _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_records"] == str(target)
    assert len(data["records"]) == 1
    record = data["records"][0]
    assert record["index"] == 0
    assert record["byte_length"] == 0
    assert isinstance(record["error"], str) and record["error"]
    assert isinstance(record["fields"], dict)
    assert data["summary"]["record_count"] == 1
    assert data["summary"]["error_count"] == 1


def test_p2p_layout_and_sample_retained():
    """Public runtime layout and sample tape remain available."""
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
    _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    error = data["records"][0]["error"]
    assert isinstance(error, str) and error
    assert data["summary"]["comp3_signed_ok"] is False
    assert data["summary"]["error_count"] >= 1


def test_f2p_invalid_odo_count_is_record_error():
    """BIN-COUNT outside the OCCURS bounds is reported as a record error."""
    target = Path("/tmp/invalid-odo.dat")
    out = Path("/tmp/invalid-odo-report.json")
    target.write_bytes(_fixture_bytes("invalid-odo.hex"))
    _run(["--layout", str(LAYOUT), "--records", str(target), "--out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    record = data["records"][0]
    assert isinstance(record["error"], str) and record["error"]
    assert isinstance(record["byte_length"], int) and record["byte_length"] >= 0
    assert data["summary"]["error_count"] >= 1


def test_f2p_rerun_is_semantically_stable():
    """A second default equiv-eval run preserves the same report semantics."""
    before = _report()
    cp = _run()
    assert cp.returncode == 0, cp.stderr
    assert _report() == before
