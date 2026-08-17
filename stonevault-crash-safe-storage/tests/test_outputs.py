from __future__ import annotations

import fcntl
import os
import re
import struct
import subprocess
import zlib
from pathlib import Path

PRODUCT_ROOT = Path("/app/stonevault")
BINARY = PRODUCT_ROOT / "bin" / "stonevault"
WAL_MAGIC = 0x31575653


class Session:
    def __init__(self, data_dir: Path, *, env: dict[str, str] | None = None) -> None:
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        self.proc = subprocess.Popen(
            [str(BINARY), "--data-dir", str(data_dir)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=process_env,
        )
        ready = self._readline()
        if not ready.startswith("READY "):
            stderr = self.proc.stderr.read() if self.proc.stderr else ""
            self.force_stop()
            raise AssertionError(f"engine did not become ready: {ready!r}; stderr={stderr!r}")
        self.ready_sequence = int(ready.split()[1])

    @classmethod
    def env_only(cls, data_dir: Path) -> Session:
        obj = cls.__new__(cls)
        process_env = os.environ.copy()
        process_env["STONEVAULT_DATA"] = str(data_dir)
        obj.proc = subprocess.Popen(
            [str(BINARY)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=process_env,
        )
        ready = obj._readline()
        if not ready.startswith("READY "):
            stderr = obj.proc.stderr.read() if obj.proc.stderr else ""
            obj.force_stop()
            raise AssertionError(f"engine did not become ready: {ready!r}; stderr={stderr!r}")
        obj.ready_sequence = int(ready.split()[1])
        return obj

    def _readline(self) -> str:
        assert self.proc.stdout is not None
        return self.proc.stdout.readline().rstrip("\n")

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
        assert self.command("QUIT") == "BYE"
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


def hx(value: bytes) -> str:
    return value.hex()


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


def scan(session: Session, tx_id: int, prefix: bytes) -> list[tuple[bytes, bytes]]:
    response = session.command(f"SCAN {tx_id} {hx(prefix)}")
    parts = response.split(" ", 2)
    assert parts[0] == "ROWS", response
    count = int(parts[1])
    if count == 0:
        return []
    assert len(parts) == 3, response
    rows: list[tuple[bytes, bytes]] = []
    for item in parts[2].split(","):
        key, value = item.split("=", 1)
        rows.append((bytes.fromhex(key), bytes.fromhex(value)))
    assert len(rows) == count
    return rows


def stats(session: Session) -> dict[str, int]:
    response = session.command("STATS")
    match = re.fullmatch(r"STATS commit_seq=(\d+) keys=(\d+) wal_bytes=(\d+)", response)
    assert match, response
    return {"commit_seq": int(match.group(1)), "keys": int(match.group(2)), "wal_bytes": int(match.group(3))}


def health(session: Session) -> dict[str, str]:
    response = session.command("HEALTH")
    assert response.startswith("HEALTH "), response
    result: dict[str, str] = {}
    for field in response.removeprefix("HEALTH ").split():
        name, value = field.split("=", 1)
        result[name] = value
    return result


def open_failure(data_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BINARY), "--data-dir", str(data_dir)],
        input="",
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )


def seed_one(data_dir: Path, key: bytes = b"key", value: bytes = b"value") -> None:
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, key, value)
        assert session.commit(tx_id) == 1


def wal_records(path: Path) -> list[tuple[int, int, int]]:
    data = path.read_bytes()
    records: list[tuple[int, int, int]] = []
    pos = 0
    while pos + 12 <= len(data):
        magic, length, _crc = struct.unpack_from("<III", data, pos)
        if magic != WAL_MAGIC or pos + 12 + length > len(data):
            break
        records.append((pos, length, pos + 12))
        pos += 12 + length
    return records


def rewrite_record_crc(data: bytearray, record_start: int, payload_start: int, length: int) -> None:
    crc = zlib.crc32(data[payload_start : payload_start + length]) & 0xFFFFFFFF
    struct.pack_into("<I", data, record_start + 8, crc)


def test_product_tree_keeps_native_language_boundary() -> None:
    """The delivered product contains native C++ and Rust sources and no Python or Go implementation files."""
    assert BINARY.is_file() and os.access(BINARY, os.X_OK)
    files = [path for path in PRODUCT_ROOT.rglob("*") if path.is_file()]
    assert any(path.suffix == ".cpp" for path in files)
    assert any(path.suffix == ".rs" for path in files)
    assert not [path for path in files if path.suffix in {".py", ".go"} or path.name in {"go.mod", "go.sum"}]


def test_lock_file_is_actively_held_by_writer(tmp_path: Path) -> None:
    """A live writer holds an advisory exclusive lock on the documented LOCK file."""
    data_dir = tmp_path / "db"
    session = Session(data_dir)
    try:
        with (data_dir / "LOCK").open("r+") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise AssertionError("LOCK was not held by the writer")
    finally:
        session.close()


def test_second_writer_is_excluded_and_lock_is_released(tmp_path: Path) -> None:
    """A concurrent writer is rejected, while a new writer can open after the first process closes."""
    data_dir = tmp_path / "db"
    first = Session(data_dir)
    try:
        second = open_failure(data_dir)
        assert second.returncode != 0
        assert "already open" in second.stderr.lower() or "writer lock" in second.stderr.lower()
    finally:
        first.close()
    with Session(data_dir) as reopened:
        assert reopened.ready_sequence == 0


def test_read_snapshot_survives_newer_put(tmp_path: Path) -> None:
    """A reader continues to observe its begin-time value after another transaction commits a replacement."""
    data_dir = tmp_path / "db"
    seed_one(data_dir, b"rate", b"old")
    with Session(data_dir) as session:
        reader = session.begin()
        writer = session.begin()
        put(session, writer, b"rate", b"new")
        assert session.commit(writer) == 2
        assert get(session, reader, b"rate") == b"old"
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_read_snapshot_survives_newer_delete(tmp_path: Path) -> None:
    """A reader retains a key from its snapshot even when a later transaction deletes that key."""
    data_dir = tmp_path / "db"
    seed_one(data_dir, b"stable", b"visible")
    with Session(data_dir) as session:
        reader = session.begin()
        writer = session.begin()
        delete(session, writer, b"stable")
        assert session.commit(writer) == 2
        assert get(session, reader, b"stable") == b"visible"
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_scan_snapshot_excludes_later_insert(tmp_path: Path) -> None:
    """A prefix scan does not acquire keys committed after the scanning transaction began."""
    data_dir = tmp_path / "db"
    seed_one(data_dir, b"p/a", b"1")
    with Session(data_dir) as session:
        reader = session.begin()
        writer = session.begin()
        put(session, writer, b"p/b", b"2")
        assert session.commit(writer) == 2
        assert scan(session, reader, b"p/") == [(b"p/a", b"1")]
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_scan_snapshot_retains_later_delete(tmp_path: Path) -> None:
    """A prefix scan retains rows that existed in its snapshot even if a newer commit deletes them."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        seed = session.begin()
        put(session, seed, b"p/a", b"1")
        put(session, seed, b"p/b", b"2")
        assert session.commit(seed) == 1
        reader = session.begin()
        writer = session.begin()
        delete(session, writer, b"p/b")
        assert session.commit(writer) == 2
        assert scan(session, reader, b"p/") == [(b"p/a", b"1"), (b"p/b", b"2")]
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_scan_applies_local_put_overlay(tmp_path: Path) -> None:
    """A transaction's own newly inserted matching row appears in its prefix scan before commit."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"p/local", b"v")
        assert scan(session, tx_id, b"p/") == [(b"p/local", b"v")]
        assert session.command(f"ROLLBACK {tx_id}") == "OK"


def test_scan_applies_local_delete_overlay(tmp_path: Path) -> None:
    """A transaction's own delete removes the matching row from its scan without changing committed state."""
    data_dir = tmp_path / "db"
    seed_one(data_dir, b"p/remove", b"v")
    with Session(data_dir) as session:
        tx_id = session.begin()
        delete(session, tx_id, b"p/remove")
        assert scan(session, tx_id, b"p/") == []
        assert session.command(f"ROLLBACK {tx_id}") == "OK"


def test_scan_uses_unsigned_byte_order(tmp_path: Path) -> None:
    """Prefix scan ordering compares key bytes as unsigned values rather than signed characters or text."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        for key in [b"\x10\xff", b"\x10\x7f", b"\x10\x00", b"\x10\x80"]:
            put(session, tx_id, key, key)
        assert session.commit(tx_id) == 1
        reader = session.begin()
        assert [key for key, _ in scan(session, reader, b"\x10")] == [b"\x10\x00", b"\x10\x7f", b"\x10\x80", b"\x10\xff"]
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_stale_put_conflicts_with_newer_version(tmp_path: Path) -> None:
    """A transaction that writes a key changed after its snapshot receives ERR CONFLICT."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        stale = session.begin()
        winner = session.begin()
        put(session, stale, b"same", b"old")
        put(session, winner, b"same", b"new")
        assert session.commit(winner) == 1
        assert session.command(f"COMMIT {stale}") == "ERR CONFLICT"


def test_stale_delete_conflicts_with_newer_version(tmp_path: Path) -> None:
    """A stale delete conflicts when another transaction committed a newer value for that key."""
    data_dir = tmp_path / "db"
    seed_one(data_dir, b"same", b"seed")
    with Session(data_dir) as session:
        stale = session.begin()
        winner = session.begin()
        delete(session, stale, b"same")
        put(session, winner, b"same", b"new")
        assert session.commit(winner) == 2
        assert session.command(f"COMMIT {stale}") == "ERR CONFLICT"


def test_conflicted_multi_key_commit_is_atomic(tmp_path: Path) -> None:
    """A conflict on one key prevents every other write in that transaction from becoming visible."""
    data_dir = tmp_path / "db"
    seed_one(data_dir, b"hot", b"seed")
    with Session(data_dir) as session:
        stale = session.begin()
        winner = session.begin()
        put(session, stale, b"hot", b"loser")
        put(session, stale, b"cold", b"must-not-publish")
        put(session, winner, b"hot", b"winner")
        assert session.commit(winner) == 2
        assert session.command(f"COMMIT {stale}") == "ERR CONFLICT"
        reader = session.begin()
        assert get(session, reader, b"hot") == b"winner"
        assert get(session, reader, b"cold") is None
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_conflict_does_not_consume_commit_sequence(tmp_path: Path) -> None:
    """Rejected stale commits leave the durable sequence unchanged and the following success gets the next sequence."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        stale = session.begin()
        winner = session.begin()
        put(session, stale, b"k", b"stale")
        put(session, winner, b"k", b"winner")
        assert session.commit(winner) == 1
        assert session.command(f"COMMIT {stale}") == "ERR CONFLICT"
        assert stats(session)["commit_seq"] == 1
        next_tx = session.begin()
        put(session, next_tx, b"next", b"v")
        assert session.commit(next_tx) == 2


def test_killed_transaction_is_invisible_after_restart(tmp_path: Path) -> None:
    """WAL mutation records from a process killed before COMMIT do not become committed during recovery."""
    data_dir = tmp_path / "db"
    crashed = Session(data_dir)
    tx_id = crashed.begin()
    put(crashed, tx_id, b"half", b"written")
    crashed.force_stop()
    with Session(data_dir) as restarted:
        assert restarted.ready_sequence == 0
        reader = restarted.begin()
        assert get(restarted, reader, b"half") is None
        assert restarted.command(f"ROLLBACK {reader}") == "OK"


def test_rolled_back_transaction_is_invisible_after_restart(tmp_path: Path) -> None:
    """Rollback leaves prior WAL mutation records uncommitted across a later process restart."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"rolled", b"back")
        assert session.command(f"ROLLBACK {tx_id}") == "OK"
    with Session(data_dir) as restarted:
        assert restarted.ready_sequence == 0
        reader = restarted.begin()
        assert get(restarted, reader, b"rolled") is None
        assert restarted.command(f"ROLLBACK {reader}") == "OK"


def test_short_final_wal_header_is_repaired(tmp_path: Path) -> None:
    """A short final WAL header is a recoverable torn tail and is truncated to the last complete record."""
    data_dir = tmp_path / "db"
    seed_one(data_dir)
    wal = data_dir / "wal.log"
    valid = wal.stat().st_size
    with wal.open("ab") as handle:
        handle.write(b"SVW1\x10")
    with Session(data_dir) as restarted:
        assert restarted.ready_sequence == 1
    assert wal.stat().st_size == valid


def test_short_final_wal_payload_is_repaired(tmp_path: Path) -> None:
    """A complete final WAL header with a short payload is truncated without losing earlier committed history."""
    data_dir = tmp_path / "db"
    seed_one(data_dir)
    wal = data_dir / "wal.log"
    valid = wal.stat().st_size
    with wal.open("ab") as handle:
        handle.write(struct.pack("<III", WAL_MAGIC, 20, 0))
        handle.write(b"abc")
    with Session(data_dir) as restarted:
        assert restarted.ready_sequence == 1
    assert wal.stat().st_size == valid


def test_complete_wal_checksum_damage_is_fatal(tmp_path: Path) -> None:
    """Checksum corruption in a complete WAL record fails database open instead of being truncated as a torn tail."""
    data_dir = tmp_path / "db"
    seed_one(data_dir)
    wal = data_dir / "wal.log"
    data = bytearray(wal.read_bytes())
    _start, length, payload = wal_records(wal)[0]
    assert length > 0
    data[payload] ^= 1
    wal.write_bytes(data)
    result = open_failure(data_dir)
    assert result.returncode != 0 and "WAL corruption" in result.stderr


def test_complete_wal_bad_magic_is_fatal(tmp_path: Path) -> None:
    """Bad magic on a complete WAL record is corruption and cannot be silently discarded."""
    data_dir = tmp_path / "db"
    seed_one(data_dir)
    wal = data_dir / "wal.log"
    data = bytearray(wal.read_bytes())
    struct.pack_into("<I", data, 0, 0xDEADBEEF)
    wal.write_bytes(data)
    result = open_failure(data_dir)
    assert result.returncode != 0 and "WAL corruption" in result.stderr


def test_non_contiguous_commit_sequence_is_fatal(tmp_path: Path) -> None:
    """Recovery rejects a validly checksummed COMMIT whose sequence skips the contiguous durable history."""
    data_dir = tmp_path / "db"
    seed_one(data_dir)
    wal = data_dir / "wal.log"
    records = wal_records(wal)
    commit_start, length, payload_start = records[-1]
    data = bytearray(wal.read_bytes())
    assert data[payload_start] == 3
    struct.pack_into("<Q", data, payload_start + 9, 7)
    rewrite_record_crc(data, commit_start, payload_start, length)
    wal.write_bytes(data)
    result = open_failure(data_dir)
    assert result.returncode != 0 and "WAL corruption" in result.stderr


def test_checkpoint_refuses_active_transaction(tmp_path: Path) -> None:
    """Maintenance cannot checkpoint a database while any transaction remains active."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"k", b"v")
        assert session.command("CHECKPOINT") == "ERR BUSY"
        assert session.command(f"ROLLBACK {tx_id}") == "OK"


def test_checkpoint_reclaims_wal_after_commit(tmp_path: Path) -> None:
    """A successful checkpoint publishes state and leaves wal.log at exactly zero bytes."""
    data_dir = tmp_path / "db"
    seed_one(data_dir)
    with Session(data_dir) as session:
        assert stats(session)["wal_bytes"] > 0
        assert session.command("CHECKPOINT") == "OK CHECKPOINT 1"
        assert stats(session)["wal_bytes"] == 0
        assert (data_dir / "wal.log").stat().st_size == 0


def test_checkpoint_restart_preserves_sequence_and_rows(tmp_path: Path) -> None:
    """Restarting after checkpoint restores the checkpoint sequence and all committed rows without WAL replay."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"a", b"1")
        put(session, tx_id, b"b", b"2")
        assert session.commit(tx_id) == 1
        assert session.command("CHECKPOINT") == "OK CHECKPOINT 1"
    with Session(data_dir) as restarted:
        assert restarted.ready_sequence == 1
        reader = restarted.begin()
        assert get(restarted, reader, b"a") == b"1"
        assert get(restarted, reader, b"b") == b"2"
        assert restarted.command(f"ROLLBACK {reader}") == "OK"


def test_snapshot_checksum_corruption_is_fatal(tmp_path: Path) -> None:
    """A published snapshot row with a damaged checksum causes open to fail closed."""
    data_dir = tmp_path / "db"
    seed_one(data_dir)
    with Session(data_dir) as session:
        assert session.command("CHECKPOINT") == "OK CHECKPOINT 1"
    snapshot = data_dir / "snapshot.dat"
    data = bytearray(snapshot.read_bytes())
    assert len(data) > 28
    data[-1] ^= 1
    snapshot.write_bytes(data)
    result = open_failure(data_dir)
    assert result.returncode != 0 and "snapshot corruption" in result.stderr


def test_snapshot_trailing_bytes_are_fatal(tmp_path: Path) -> None:
    """Bytes after the declared snapshot rows are rejected instead of being accepted as an alternate disk format."""
    data_dir = tmp_path / "db"
    seed_one(data_dir)
    with Session(data_dir) as session:
        assert session.command("CHECKPOINT") == "OK CHECKPOINT 1"
    with (data_dir / "snapshot.dat").open("ab") as handle:
        handle.write(b"junk")
    result = open_failure(data_dir)
    assert result.returncode != 0 and "snapshot corruption" in result.stderr


def test_stale_snapshot_temporary_is_removed_on_open(tmp_path: Path) -> None:
    """An abandoned snapshot.tmp from an interrupted checkpoint is discarded during the next successful open."""
    data_dir = tmp_path / "db"
    seed_one(data_dir)
    temporary = data_dir / "snapshot.tmp"
    temporary.write_bytes(b"abandoned")
    with Session(data_dir) as restarted:
        assert restarted.ready_sequence == 1
    assert not temporary.exists()


def test_explicit_data_directory_overrides_environment(tmp_path: Path) -> None:
    """The command-line data directory has higher precedence than STONEVAULT_DATA when both are supplied."""
    cli_dir = tmp_path / "cli"
    env_dir = tmp_path / "env"
    env = os.environ.copy()
    env["STONEVAULT_DATA"] = str(env_dir)
    proc = subprocess.Popen(
        [str(BINARY), "--data-dir", str(cli_dir)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )
    assert proc.stdout is not None and proc.stdin is not None
    assert proc.stdout.readline().startswith("READY 0")
    proc.stdin.write("QUIT\n")
    proc.stdin.flush()
    assert proc.stdout.readline().strip() == "BYE"
    proc.wait(timeout=5)
    assert (cli_dir / "wal.log").exists()
    assert not (env_dir / "wal.log").exists()


def test_exact_key_limit_is_accepted(tmp_path: Path) -> None:
    """A key exactly 4096 decoded bytes is valid and can be committed and read back."""
    data_dir = tmp_path / "db"
    key = bytes(range(256)) * 16
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, key, b"ok")
        assert get(session, tx_id, key) == b"ok"
        assert session.commit(tx_id) == 1


def test_exact_value_limit_is_accepted(tmp_path: Path) -> None:
    """A value exactly 1048576 decoded bytes is accepted at the inclusive protocol boundary."""
    data_dir = tmp_path / "db"
    value = b"z" * (1024 * 1024)
    with Session(data_dir) as session:
        tx_id = session.begin()
        put(session, tx_id, b"big", value)
        assert get(session, tx_id, b"big") == value
        assert session.commit(tx_id) == 1


def test_health_reports_active_transactions(tmp_path: Path) -> None:
    """HEALTH reports the live active transaction count rather than only durable state."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        report = health(session)
        assert report["status"] == "ok"
        assert report["active_tx"] == "1"
        assert session.command(f"ROLLBACK {tx_id}") == "OK"
        assert health(session)["active_tx"] == "0"


def test_health_tracks_published_snapshot(tmp_path: Path) -> None:
    """HEALTH distinguishes the absence of a snapshot from a successfully published checkpoint snapshot."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        assert health(session)["snapshot"] == "absent"
        tx_id = session.begin()
        put(session, tx_id, b"k", b"v")
        assert session.commit(tx_id) == 1
        assert session.command("CHECKPOINT") == "OK CHECKPOINT 1"
        report = health(session)
        assert report["snapshot"] == "present"
        assert report["commit_seq"] == "1"
        assert report["keys"] == "1"
        assert report["wal_bytes"] == "0"


def test_stats_match_durable_state_and_file_size(tmp_path: Path) -> None:
    """STATS remains consistent with committed visible rows and the actual WAL file size."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        first = session.begin()
        put(session, first, b"a", b"1")
        put(session, first, b"b", b"2")
        assert session.commit(first) == 1
        second = session.begin()
        delete(session, second, b"a")
        assert session.commit(second) == 2
        report = stats(session)
        assert report == {"commit_seq": 2, "keys": 1, "wal_bytes": (data_dir / "wal.log").stat().st_size}


def test_oversized_inputs_are_rejected_without_terminating(tmp_path: Path) -> None:
    """Inputs above documented key/value limits return ERR and the same process remains usable."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        too_big_key = "aa" * 4097
        assert session.command(f"PUT {tx_id} {too_big_key} 00").startswith("ERR ")
        too_big_value = "bb" * (1024 * 1024 + 1)
        assert session.command(f"PUT {tx_id} 6b {too_big_value}").startswith("ERR ")
        put(session, tx_id, b"ok", b"still-alive")
        assert session.commit(tx_id) == 1


def test_malformed_commands_and_unknown_transactions_do_not_kill_session(tmp_path: Path) -> None:
    """Protocol errors are returned in-band and do not prevent later valid transaction work."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        assert session.command("PUT nope").startswith("ERR ")
        assert session.command("GET 999 6b").startswith("ERR ")
        assert session.command("GET 1 abc").startswith("ERR ")
        tx_id = session.begin()
        put(session, tx_id, b"ok", b"yes")
        assert session.commit(tx_id) == 1


def test_hex_input_is_case_insensitive_and_output_is_lowercase(tmp_path: Path) -> None:
    """Hexadecimal command operands accept uppercase digits while values and scan rows use canonical lowercase output."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        tx_id = session.begin()
        assert session.command(f"PUT {tx_id} A0FF CAFE") == "OK"
        assert session.command(f"GET {tx_id} A0FF") == "VALUE cafe"
        assert session.command(f"SCAN {tx_id} A0") == "ROWS 1 a0ff=cafe"
        assert session.command(f"ROLLBACK {tx_id}") == "OK"
