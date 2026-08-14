"""Strict packed-decimal contract cases not covered by the original holdouts."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path("/app/equiv")
BIN = ROOT / "bin" / "equiv-eval"
LAYOUT = ROOT / "programs" / "skumast.layout"
PUBLIC = ROOT / "samples" / "sku-public.dat"


def _mutate_nibble(blob: bytes, byte_offset: int, nibble: int, *, low: bool) -> bytes:
    data = bytearray(blob)
    current = data[byte_offset]
    if low:
        data[byte_offset] = (current & 0xF0) | nibble
    else:
        data[byte_offset] = (nibble << 4) | (current & 0x0F)
    return bytes(data)


def _evaluate(blob: bytes, name: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    target = Path(f"/tmp/{name}.dat")
    out = Path(f"/tmp/{name}.json")
    target.write_bytes(blob)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    cp = subprocess.run(
        [str(BIN), "--layout", str(LAYOUT), "--records", str(target), "--out", str(out)],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return cp, json.loads(out.read_text(encoding="utf-8"))


def _assert_record_error(data: dict) -> None:
    record = data["records"][0]
    assert isinstance(record["error"], str) and record["error"]
    assert isinstance(record["byte_length"], int) and record["byte_length"] >= 0
    assert data["summary"]["error_count"] >= 1


def test_f2p_signed_field_rejects_unsigned_f_sign():
    """A signed QOH field accepts C/D only; F is an unsigned sign, not positive signed."""
    # Record 0 QOH occupies bytes 12..16; byte 16 low nibble is its sign.
    malformed = _mutate_nibble(PUBLIC.read_bytes(), 16, 0xF, low=True)
    _, data = _evaluate(malformed, "signed-qoh-with-f")
    _assert_record_error(data)
    assert data["summary"]["comp3_signed_ok"] is False


def test_f2p_unsigned_field_rejects_signed_c_and_d_signs():
    """Unsigned REORDER-PT accepts F only; signed C and D must both be rejected."""
    # Record 0 REORDER-PT occupies bytes 23..25; byte 25 low nibble is its sign.
    public = PUBLIC.read_bytes()
    for sign, label in ((0xC, "c"), (0xD, "d")):
        malformed = _mutate_nibble(public, 25, sign, low=True)
        _, data = _evaluate(malformed, f"unsigned-reorder-with-{label}")
        _assert_record_error(data)
        assert data["summary"]["comp3_signed_ok"] is False


def test_f2p_comp3_requires_zero_left_pad_nibble():
    """Even-digit COMP-3 fields reject a non-zero storage pad nibble as a record error."""
    # UNIT-COST has eight digits in five bytes. Byte 17 high nibble is the required pad.
    malformed = _mutate_nibble(PUBLIC.read_bytes(), 17, 0x9, low=False)
    _, data = _evaluate(malformed, "unit-cost-nonzero-pad")
    _assert_record_error(data)


def test_f2p_comp3_rejects_nondecimal_digit_nibble():
    """A-F in a COMP-3 digit position is rejected while sign and framing bytes stay valid."""
    # QOH has nine digits and no storage pad. Byte 12 high nibble is its first digit.
    malformed = _mutate_nibble(PUBLIC.read_bytes(), 12, 0xA, low=False)
    _, data = _evaluate(malformed, "qoh-nondecimal-digit")
    _assert_record_error(data)
