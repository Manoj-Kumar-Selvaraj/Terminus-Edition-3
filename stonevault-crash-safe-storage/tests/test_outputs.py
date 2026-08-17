from __future__ import annotations

import os
import re
import struct
import subprocess
from pathlib import Path

PRODUCT_ROOT = Path("/app/stonevault")
BINARY = PRODUCT_ROOT / "bin" / "stonevault"


class Session:
    def __init__(self, data_dir: Path, *, use_env: bool = False) -> None:
        env = os.environ.copy()
        if use_env:
            env["STONEVAULT_DATA"] = str(data_dir)
            argv = [str(BINARY)]
        else:
            argv = [str(BINARY), "--data-dir", str(data_dir)]
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        ready = self._readline()
        if not ready.startswith("READY "):
            stderr = self.proc.stderr.read() if self.proc.stderr else ""
            self.force_stop()
            raise AssertionError(f"engine did not become ready: {ready!r}; stderr={stderr!r}")
        self.ready_sequence = int(ready.split()[1])

    def _readline(self) -> str:
        assert self.proc.stdout is not None
        line = self.proc.stdout.readline()
        return line.rstrip("\n")

    def command(self, line: str) -> str:
        assert self.proc.stdin is not None
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        return self._readline()

    def begin(self) -> int:
        response = self.command("BEGIN")
        match = re.fullmatch(r"OK BEGIN (\d+)", response)
        assert match, response
        return int(match.group(1))

    def commit(self, tx_id: int) -> int:
        response = self.command(f"COMMIT {tx_id}")
        match = re.fullmatch(r"OK COMMIT (\d+)", response)
        assert match, response
        return int(match.group(1))

    def close(self) -> None:
        if self.proc.poll() is not None:
            return
        response = self.command("QUIT")
        assert response == "BYE"
        self.proc.wait(timeout=5)
        assert self.proc.returncode == 0

    def force_stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)

    def __enter__(self) -> Session:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.close()
        else:
            self.force_stop()


def hx(data: bytes) -> str:
    return data.hex()


def put(session: Session, tx_id: int, key: bytes, value: bytes) -> None:
    assert session.command(f"PUT {tx_id} {hx(key)} {hx(value)}") == "OK"


def delete(session: Session, tx_id: int, key: bytes) -> None:
    assert session.command(f"DEL {tx_id} {hx(key)}") == "OK"


def get(session: Session, tx_id: int, key: bytes) -> bytes | None:
    response = session.command(f"GET {tx_id} {hx(key)}")
    if response == "NOT_FOUND":
        return None
    assert response.startswith("VALUE "), response
    return bytes.fromhex(response.split(" ", 1)[1])


def parse_rows(response: str) -> list[tuple[bytes, bytes]]:
    fields = response.split(" ", 2)
    assert fields[0] == "ROWS", response
    count = int(fields[1])
    if count == 0:
        assert len(fields) == 2, response
        return []
    assert len(fields) == 3, response
    rows = []
    for item in fields[2].split(","):
        key_hex, value_hex = item.split("=", 1)
        rows.append((bytes.fromhex(key_hex), bytes.fromhex(value_hex)))
    assert len(rows) == count
    return rows


def parse_stats(response: str) -> dict[str, int]:
    match = re.fullmatch(r"STATS commit_seq=(\d+) keys=(\d+) wal_bytes=(\d+)", response)
    assert match, response
    return {
        "commit_seq": int(match.group(1)),
        "keys": int(match.group(2)),
        "wal_bytes": int(match.group(3)),
    }


def test_product_tree_uses_only_native_implementation_languages() -> None:
    """The submitted product contains C++ and Rust sources but no Python or Go implementation files."""
    assert BINARY.is_file(), "rebuilt native binary is missing"
    assert os.access(BINARY, os.X_OK), "rebuilt native binary is not executable"
    files = [path for path in PRODUCT_ROOT.rglob("*") if path.is_file()]
    suffixes = {path.suffix for path in files}
    assert ".rs" in suffixes
    assert ".cpp" in suffixes
    forbidden = [
        path
        for path in files
        if path.suffix in {".py", ".go"} or path.name in {"go.mod", "go.sum"}
    ]
    assert forbidden == []


def test_cli_environment_validation_and_basic_delete_flow(tmp_path: Path) -> None:
    """The Rust CLI honors its environment data directory, validates commands, and implements delete semantics."""
    data_dir = tmp_path / "db"
    with Session(data_dir, use_env=True) as session:
        assert session.ready_sequence == 0
        assert session.command("PUT nope") == "ERR invalid command"
        assert session.command("GET 1 abc") == "ERR key must be even-length hexadecimal"
        tx_id = session.begin()
        put(session, tx_id, b"alpha", b"one")
        assert get(session, tx_id, b"alpha") == b"one"
        delete(session, tx_id, b"alpha")
        assert get(session, tx_id, b"alpha") is None
        assert session.commit(tx_id) == 1


def test_committed_value_survives_restart(tmp_path: Path) -> None:
    """A successful commit is durable and receives a contiguous sequence that is restored on open."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"account/7", b"settled")
        assert session.commit(tx_id) == 1
    with Session(data_dir) as restarted:
        assert restarted.ready_sequence == 1
        tx_id = restarted.begin()
        assert get(restarted, tx_id, b"account/7") == b"settled"
        assert restarted.command(f"ROLLBACK {tx_id}") == "OK"


def test_rollback_and_killed_transaction_remain_invisible(tmp_path: Path) -> None:
    """Rolled-back and crash-interrupted WAL mutations never become visible after recovery."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"rolled", b"back")
        assert session.command(f"ROLLBACK {tx_id}") == "OK"

    crashed = Session(data_dir)
    tx_id = crashed.begin()
    put(crashed, tx_id, b"half", b"written")
    crashed.force_stop()

    with Session(data_dir) as restarted:
        tx_id = restarted.begin()
        assert get(restarted, tx_id, b"rolled") is None
        assert get(restarted, tx_id, b"half") is None
        assert restarted.command(f"ROLLBACK {tx_id}") == "OK"


def test_snapshot_reads_remain_stable_across_newer_commit(tmp_path: Path) -> None:
    """A transaction continues reading its begin-time snapshot after another transaction commits a new version."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        seed = session.begin()
        put(session, seed, b"rate", b"old")
        assert session.commit(seed) == 1

        reader = session.begin()
        writer = session.begin()
        put(session, writer, b"rate", b"new")
        assert session.commit(writer) == 2
        assert get(session, reader, b"rate") == b"old"
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_stale_writer_commit_is_rejected_without_advancing_sequence(tmp_path: Path) -> None:
    """Concurrent writes to the same key detect a stale snapshot and the conflicted commit publishes nothing."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        first = session.begin()
        second = session.begin()
        put(session, first, b"same", b"winner")
        put(session, second, b"same", b"loser")
        assert session.commit(first) == 1
        assert session.command(f"COMMIT {second}") == "ERR CONFLICT"
        stats = parse_stats(session.command("STATS"))
        assert stats["commit_seq"] == 1
        reader = session.begin()
        assert get(session, reader, b"same") == b"winner"
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_prefix_scan_is_byte_ordered_snapshot_consistent_and_overlay_aware(tmp_path: Path) -> None:
    """Prefix scans use unsigned byte order, preserve the transaction snapshot, and overlay local puts and deletes."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        seed = session.begin()
        for key, value in [
            (b"\x10\x80", b"c"),
            (b"\x10\x00", b"a"),
            (b"\x10\xff", b"d"),
            (b"\x10\x7f", b"b"),
            (b"\x11\x00", b"outside"),
        ]:
            put(session, seed, key, value)
        assert session.commit(seed) == 1

        scanner = session.begin()
        newer = session.begin()
        put(session, newer, b"\x10\x40", b"newer")
        assert session.commit(newer) == 2

        delete(session, scanner, b"\x10\x7f")
        put(session, scanner, b"\x10\x20", b"local")
        rows = parse_rows(session.command(f"SCAN {scanner} 10"))
        assert rows == [
            (b"\x10\x00", b"a"),
            (b"\x10\x20", b"local"),
            (b"\x10\x80", b"c"),
            (b"\x10\xff", b"d"),
        ]
        assert session.command(f"ROLLBACK {scanner}") == "OK"


def test_short_wal_tail_is_discarded_without_losing_committed_state(tmp_path: Path) -> None:
    """A physically short final WAL record is treated as a torn tail and truncated to the last complete record."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"safe", b"value")
        assert session.commit(tx_id) == 1
    wal = data_dir / "wal.log"
    valid_size = wal.stat().st_size
    with wal.open("ab") as handle:
        handle.write(b"SVW1\x05\x00\x00")
    assert wal.stat().st_size > valid_size

    with Session(data_dir) as restarted:
        assert restarted.ready_sequence == 1
        tx_id = restarted.begin()
        assert get(restarted, tx_id, b"safe") == b"value"
        assert restarted.command(f"ROLLBACK {tx_id}") == "OK"
    assert wal.stat().st_size == valid_size


def test_checksum_corruption_in_complete_wal_record_is_fatal(tmp_path: Path) -> None:
    """Checksum damage in a complete WAL record is reported as corruption instead of being mistaken for a torn tail."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"first", b"one")
        assert session.commit(tx_id) == 1
        tx_id = session.begin()
        put(session, tx_id, b"second", b"two")
        assert session.commit(tx_id) == 2

    wal = data_dir / "wal.log"
    content = bytearray(wal.read_bytes())
    assert len(content) >= 13
    magic, payload_length, _ = struct.unpack_from("<III", content, 0)
    assert magic == 0x31575653
    assert payload_length > 0
    content[12] ^= 0x01
    wal.write_bytes(content)

    result = subprocess.run(
        [str(BINARY), "--data-dir", str(data_dir)],
        input="",
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0
    assert "WAL corruption" in result.stderr
    assert "READY" not in result.stdout


def test_checkpoint_is_busy_with_open_transaction_then_reclaims_wal(tmp_path: Path) -> None:
    """Checkpoint refuses active transactions, then atomically preserves committed data while reducing WAL size to zero."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"keep", b"forever")
        assert session.command("CHECKPOINT") == "ERR BUSY"
        assert session.commit(tx_id) == 1
        before = parse_stats(session.command("STATS"))
        assert before["wal_bytes"] > 0
        assert session.command("CHECKPOINT") == "OK CHECKPOINT 1"
        after = parse_stats(session.command("STATS"))
        assert after == {"commit_seq": 1, "keys": 1, "wal_bytes": 0}
        assert (data_dir / "snapshot.dat").is_file()
        assert (data_dir / "wal.log").stat().st_size == 0

    with Session(data_dir) as restarted:
        assert restarted.ready_sequence == 1
        tx_id = restarted.begin()
        assert get(restarted, tx_id, b"keep") == b"forever"
        assert restarted.command(f"ROLLBACK {tx_id}") == "OK"


def test_second_writer_is_excluded_until_first_process_closes(tmp_path: Path) -> None:
    """The database directory lock prevents a second live writer and is released when the first process exits."""
    data_dir = tmp_path / "db"
    first = Session(data_dir)
    try:
        second = subprocess.run(
            [str(BINARY), "--data-dir", str(data_dir)],
            input="",
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        assert second.returncode != 0
        assert "writer lock" in second.stderr.lower()
    finally:
        first.close()

    with Session(data_dir) as reopened:
        assert reopened.ready_sequence == 0


def test_stats_reflect_durable_keys_sequence_and_wal_file_size(tmp_path: Path) -> None:
    """STATS reports the durable sequence, visible key count, and exact current WAL byte size after updates and deletes."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        first = session.begin()
        put(session, first, b"a", b"1")
        put(session, first, b"b", b"2")
        assert session.commit(first) == 1
        second = session.begin()
        delete(session, second, b"a")
        put(session, second, b"c", b"3")
        assert session.commit(second) == 2
        stats = parse_stats(session.command("STATS"))
        assert stats["commit_seq"] == 2
        assert stats["keys"] == 2
        assert stats["wal_bytes"] == (data_dir / "wal.log").stat().st_size


def test_binary_data_and_documented_size_boundaries(tmp_path: Path) -> None:
    """Arbitrary binary data and maximum key/value sizes round-trip while values or keys above the limits are rejected."""
    data_dir = tmp_path / "db"
    max_key = bytes((i % 251 for i in range(4096)))
    max_value = bytes((i % 253 for i in range(1024 * 1024)))
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, max_key, max_value)
        assert session.commit(tx_id) == 1
        reader = session.begin()
        assert get(session, reader, max_key) == max_value
        assert session.command(f"ROLLBACK {reader}") == "OK"

        too_large_value = b"x" * (1024 * 1024 + 1)
        tx_id = session.begin()
        response = session.command(f"PUT {tx_id} 6b {too_large_value.hex()}")
        assert response.startswith("ERR value exceeds 1048576 bytes")
        assert session.command(f"ROLLBACK {tx_id}") == "OK"

        too_large_key = b"k" * 4097
        tx_id = session.begin()
        response = session.command(f"DEL {tx_id} {too_large_key.hex()}")
        assert response.startswith("ERR key exceeds 4096 bytes")
        assert session.command(f"ROLLBACK {tx_id}") == "OK"
