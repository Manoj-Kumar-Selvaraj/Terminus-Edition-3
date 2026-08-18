from __future__ import annotations

import struct
from pathlib import Path

from test_outputs import Session, get, open_failure, put, scan


def _checkpoint_snapshot(data_dir: Path, rows: list[tuple[bytes, bytes]]) -> Path:
    with Session(data_dir) as session:
        tx_id = session.begin()
        for key, value in rows:
            put(session, tx_id, key, value)
        assert session.commit(tx_id) == 1
        assert session.command("CHECKPOINT") == "OK CHECKPOINT 1"
    return data_dir / "snapshot.dat"


def _snapshot_record_ranges(data: bytes) -> list[tuple[int, int]]:
    assert data[:8] == b"SVSNAP1\x00"
    row_count = struct.unpack_from("<Q", data, 16)[0]
    pos = 24
    ranges: list[tuple[int, int]] = []
    for _ in range(row_count):
        start = pos
        key_len, value_len = struct.unpack_from("<II", data, pos)
        pos += 8 + key_len + value_len + 4
        ranges.append((start, pos))
    return ranges


def test_environment_only_data_directory_is_honored(tmp_path: Path) -> None:
    """STONEVAULT_DATA selects the database directory when no explicit --data-dir is supplied."""
    env_dir = tmp_path / "env-db"
    with Session.env_only(env_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"env", b"selected")
        assert session.commit(tx_id) == 1
    assert (env_dir / "wal.log").exists()
    assert (env_dir / "LOCK").exists()


def test_exact_scan_prefix_limit_is_accepted(tmp_path: Path) -> None:
    """A SCAN prefix exactly 4096 decoded bytes is valid at the inclusive protocol boundary."""
    data_dir = tmp_path / "db"
    prefix = bytes(range(256)) * 16
    with Session(data_dir) as session:
        tx_id = session.begin()
        assert scan(session, tx_id, prefix) == []
        assert session.command(f"ROLLBACK {tx_id}") == "OK"


def test_oversized_scan_prefix_is_rejected_without_terminating(tmp_path: Path) -> None:
    """A SCAN prefix above 4096 decoded bytes returns ERR while the process remains usable."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        too_big_prefix = "aa" * 4097
        assert session.command(f"SCAN {tx_id} {too_big_prefix}").startswith("ERR ")
        put(session, tx_id, b"ok", b"alive")
        assert get(session, tx_id, b"ok") == b"alive"
        assert session.command(f"ROLLBACK {tx_id}") == "OK"


def test_arbitrary_binary_key_and_value_round_trip(tmp_path: Path) -> None:
    """Binary keys and values including NUL and high-bit bytes survive commit and restart exactly."""
    data_dir = tmp_path / "db"
    key = bytes([0x00, 0x01, 0x7F, 0x80, 0xFE, 0xFF, 0x10])
    value = bytes(range(256)) + b"\x00\xff\x00\x80"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, key, value)
        assert session.commit(tx_id) == 1
    with Session(data_dir) as restarted:
        tx_id = restarted.begin()
        assert get(restarted, tx_id, key) == value
        assert restarted.command(f"ROLLBACK {tx_id}") == "OK"


def test_committed_hex_output_is_canonical(tmp_path: Path) -> None:
    """Uppercase hexadecimal input is accepted and committed GET/SCAN output is lowercase without relying on a local scan overlay."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        assert session.command(f"PUT {tx_id} A0FF CAFE") == "OK"
        assert session.commit(tx_id) == 1
        reader = session.begin()
        assert session.command(f"GET {reader} A0FF") == "VALUE cafe"
        assert session.command(f"SCAN {reader} A0") == "ROWS 1 a0ff=cafe"
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_snapshot_bad_magic_is_fatal(tmp_path: Path) -> None:
    """A published snapshot with invalid magic is rejected rather than interpreted as another format."""
    data_dir = tmp_path / "db"
    snapshot = _checkpoint_snapshot(data_dir, [(b"a", b"1")])
    data = bytearray(snapshot.read_bytes())
    data[0] ^= 0xFF
    snapshot.write_bytes(data)
    result = open_failure(data_dir)
    assert result.returncode != 0 and "snapshot corruption" in result.stderr


def test_snapshot_truncation_is_fatal(tmp_path: Path) -> None:
    """A truncated published snapshot fails closed during open."""
    data_dir = tmp_path / "db"
    snapshot = _checkpoint_snapshot(data_dir, [(b"a", b"1")])
    data = snapshot.read_bytes()
    snapshot.write_bytes(data[:-2])
    result = open_failure(data_dir)
    assert result.returncode != 0 and "snapshot corruption" in result.stderr


def test_snapshot_impossible_row_count_is_fatal(tmp_path: Path) -> None:
    """An unreasonable snapshot row count is rejected without attempting an unsafe allocation or partial open."""
    data_dir = tmp_path / "db"
    snapshot = _checkpoint_snapshot(data_dir, [(b"a", b"1")])
    data = bytearray(snapshot.read_bytes())
    struct.pack_into("<Q", data, 16, 100000001)
    snapshot.write_bytes(data)
    result = open_failure(data_dir)
    assert result.returncode != 0 and "snapshot corruption" in result.stderr


def test_snapshot_out_of_order_rows_are_fatal(tmp_path: Path) -> None:
    """Valid row records reordered into descending byte order are rejected even though their individual CRCs remain valid."""
    data_dir = tmp_path / "db"
    snapshot = _checkpoint_snapshot(data_dir, [(b"a", b"1"), (b"b", b"2")])
    data = snapshot.read_bytes()
    ranges = _snapshot_record_ranges(data)
    assert len(ranges) == 2
    first = data[ranges[0][0] : ranges[0][1]]
    second = data[ranges[1][0] : ranges[1][1]]
    snapshot.write_bytes(data[:24] + second + first)
    result = open_failure(data_dir)
    assert result.returncode != 0 and "snapshot corruption" in result.stderr
