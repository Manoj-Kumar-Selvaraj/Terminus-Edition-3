from __future__ import annotations

import os
import re
import shutil
import signal
import struct
import subprocess
import threading
import time
import zlib
from pathlib import Path

from test_outputs import BINARY, PRODUCT_ROOT, Session, get, put, seed_one

WAL_MAGIC = 0x31575653
SNAPSHOT_MAGIC = b"SVSNAP1\0"
MAX_KEY = 4096
MAX_VALUE = 1024 * 1024
MAX_WAL_FRAME_PAYLOAD = 8 * 1024 * 1024
DEFAULT_DATA_DIR = PRODUCT_ROOT / "data"


def frame_wal(payload: bytes) -> bytes:
    """Encode one WAL frame solely from the published little-endian framing contract."""
    return struct.pack("<III", WAL_MAGIC, len(payload), zlib.crc32(payload) & 0xFFFFFFFF) + payload


def put_payload(tx_id: int, key: bytes, value: bytes) -> bytes:
    """Encode a published PUT payload independently of the product serializer."""
    return b"\x01" + struct.pack("<QII", tx_id, len(key), len(value)) + key + value


def commit_payload(tx_id: int, sequence: int) -> bytes:
    """Encode a published COMMIT payload independently of the product serializer."""
    return b"\x03" + struct.pack("<QQ", tx_id, sequence)


def snapshot_bytes(sequence: int, rows: list[tuple[bytes, bytes]]) -> bytes:
    """Encode a snapshot independently from the documented layout and row CRC rule."""
    body = bytearray(SNAPSHOT_MAGIC + struct.pack("<QQ", sequence, len(rows)))
    for key, value in rows:
        record = struct.pack("<II", len(key), len(value)) + key + value
        body.extend(record)
        body.extend(struct.pack("<I", zlib.crc32(record) & 0xFFFFFFFF))
    return bytes(body)


def run_open(data_dir: Path) -> subprocess.CompletedProcess[str]:
    """Attempt a one-shot open and capture the startup result without imposing error vocabulary."""
    return subprocess.run(
        [str(BINARY), "--data-dir", str(data_dir)],
        input="QUIT\n",
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def test_documented_default_data_directory_is_used(tmp_path: Path) -> None:
    """With no flag or environment override, startup owns the documented default data directory."""
    assert not DEFAULT_DATA_DIR.exists(), "default data directory must start isolated in the verifier image"
    env = os.environ.copy()
    env.pop("STONEVAULT_DATA", None)
    proc = subprocess.Popen(
        [str(BINARY)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )
    try:
        assert proc.stdout is not None
        assert re.fullmatch(r"READY 0", proc.stdout.readline().rstrip("\n"))
        assert (DEFAULT_DATA_DIR / "LOCK").is_file()
        assert (DEFAULT_DATA_DIR / "wal.log").is_file()
        assert proc.stdin is not None
        proc.stdin.write("QUIT\n")
        proc.stdin.flush()
        assert proc.stdout.readline().rstrip("\n") == "BYE"
        proc.wait(timeout=5)
        assert proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        shutil.rmtree(DEFAULT_DATA_DIR, ignore_errors=True)


def test_point_read_observes_own_delete(tmp_path: Path) -> None:
    """A point read observes a transaction-local delete before commit without changing durable state."""
    data_dir = tmp_path / "db"
    seed_one(data_dir, b"local-delete", b"durable")
    with Session(data_dir) as session:
        tx_id = session.begin()
        assert session.command(f"DEL {tx_id} {b'local-delete'.hex()}") == "OK"
        assert get(session, tx_id, b"local-delete") is None
        assert session.command(f"ROLLBACK {tx_id}") == "OK"
        reader = session.begin()
        assert get(session, reader, b"local-delete") == b"durable"
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_conflicted_transaction_is_ended(tmp_path: Path) -> None:
    """A rejected stale commit ends that transaction and removes it from the active transaction set."""
    data_dir = tmp_path / "db"
    with Session(data_dir) as session:
        stale = session.begin()
        winner = session.begin()
        put(session, stale, b"key", b"loser")
        put(session, winner, b"key", b"winner")
        assert session.commit(winner) == 1
        assert session.command(f"COMMIT {stale}") == "ERR CONFLICT"
        assert session.command(f"GET {stale} {b'key'.hex()}").startswith("ERR ")
        assert re.fullmatch(
            r"HEALTH status=ok commit_seq=1 keys=1 active_tx=0 wal_bytes=\d+ snapshot=(?:present|absent)",
            session.command("HEALTH"),
        )


def test_acknowledged_commit_survives_immediate_process_kill(tmp_path: Path) -> None:
    """Once COMMIT success is observed, killing the process cannot erase the acknowledged state."""
    data_dir = tmp_path / "db"
    session = Session(data_dir)
    tx_id = session.begin()
    put(session, tx_id, b"durable", b"acknowledged")
    assert session.commit(tx_id) == 1
    session.force_stop()
    with Session(data_dir) as reopened:
        assert reopened.ready_sequence == 1
        reader = reopened.begin()
        assert get(reopened, reader, b"durable") == b"acknowledged"
        assert reopened.command(f"ROLLBACK {reader}") == "OK"


def test_multi_commit_wal_prefix_replays_completely(tmp_path: Path) -> None:
    """A crash before checkpoint preserves every committed transaction in a contiguous WAL prefix."""
    data_dir = tmp_path / "db"
    session = Session(data_dir)
    for index in range(1, 4):
        tx_id = session.begin()
        put(session, tx_id, f"k{index}".encode(), f"v{index}".encode())
        assert session.commit(tx_id) == index
    session.force_stop()
    with Session(data_dir) as reopened:
        assert reopened.ready_sequence == 3
        reader = reopened.begin()
        for index in range(1, 4):
            assert get(reopened, reader, f"k{index}".encode()) == f"v{index}".encode()
        assert reopened.command(f"ROLLBACK {reader}") == "OK"


def test_independent_wal_fixture_recovers_published_layout(tmp_path: Path) -> None:
    """An independently encoded PUT plus COMMIT fixture remains readable across the public WAL ABI."""
    data_dir = tmp_path / "db"
    data_dir.mkdir()
    (data_dir / "wal.log").write_bytes(
        frame_wal(put_payload(7, b"alpha", b"beta")) + frame_wal(commit_payload(7, 1))
    )
    with Session(data_dir) as session:
        assert session.ready_sequence == 1
        reader = session.begin()
        assert get(session, reader, b"alpha") == b"beta"
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_complete_unknown_wal_type_is_fatal(tmp_path: Path) -> None:
    """A complete checksummed WAL frame with an unknown type fails closed rather than being repaired."""
    data_dir = tmp_path / "db"
    data_dir.mkdir()
    (data_dir / "wal.log").write_bytes(frame_wal(b"\x7f"))
    result = run_open(data_dir)
    assert result.returncode != 0
    assert "WAL corruption" in result.stderr


def test_complete_malformed_wal_payload_is_fatal(tmp_path: Path) -> None:
    """A complete checksummed PUT frame with missing required fields is corruption."""
    data_dir = tmp_path / "db"
    data_dir.mkdir()
    malformed = b"\x01" + struct.pack("<Q", 9)
    (data_dir / "wal.log").write_bytes(frame_wal(malformed))
    result = run_open(data_dir)
    assert result.returncode != 0
    assert "WAL corruption" in result.stderr


def test_impossible_wal_frame_length_is_fatal(tmp_path: Path) -> None:
    """Complete WAL headers outside the published payload-length range are corruption, not torn tails."""
    zero_dir = tmp_path / "zero"
    zero_dir.mkdir()
    zero_header = struct.pack("<III", WAL_MAGIC, 0, zlib.crc32(b"") & 0xFFFFFFFF)
    (zero_dir / "wal.log").write_bytes(zero_header)
    zero_result = run_open(zero_dir)
    assert zero_result.returncode != 0
    assert "WAL corruption" in zero_result.stderr

    oversized_dir = tmp_path / "oversized"
    oversized_dir.mkdir()
    oversized_header = struct.pack("<III", WAL_MAGIC, MAX_WAL_FRAME_PAYLOAD + 1, 0)
    (oversized_dir / "wal.log").write_bytes(oversized_header)
    oversized_result = run_open(oversized_dir)
    assert oversized_result.returncode != 0
    assert "WAL corruption" in oversized_result.stderr


def test_checkpoint_interruption_keeps_a_durable_recovery_source(tmp_path: Path) -> None:
    """While snapshot.tmp is being published, committed WAL data remains durable enough for restart recovery."""
    data_dir = tmp_path / "db"
    session = Session(data_dir)
    tx_id = session.begin()
    value = b"x" * (16 * 1024)
    for index in range(256):
        put(session, tx_id, f"row-{index:04d}".encode(), value)
    assert session.commit(tx_id) == 1
    wal_path = data_dir / "wal.log"
    assert wal_path.stat().st_size > 0

    failure: list[BaseException] = []

    def checkpoint() -> None:
        try:
            session.command("CHECKPOINT")
        except BaseException as exc:  # process is deliberately killed mid-command
            failure.append(exc)

    thread = threading.Thread(target=checkpoint, daemon=True)
    thread.start()
    observed = False
    deadline = time.monotonic() + 10
    while thread.is_alive() and time.monotonic() < deadline:
        if (data_dir / "snapshot.tmp").exists():
            os.kill(session.proc.pid, signal.SIGSTOP)
            observed = True
            break
    assert observed, "checkpoint completed before snapshot.tmp publication could be observed"
    assert wal_path.stat().st_size > 0, "WAL was reclaimed before snapshot publication completed"
    os.kill(session.proc.pid, signal.SIGKILL)
    session.proc.wait(timeout=5)
    thread.join(timeout=5)

    with Session(data_dir) as reopened:
        assert reopened.ready_sequence == 1
        reader = reopened.begin()
        assert get(reopened, reader, b"row-0000") == value
        assert get(reopened, reader, b"row-0255") == value
        assert reopened.command(f"ROLLBACK {reader}") == "OK"


def test_independent_snapshot_fixture_preserves_layout_and_crc(tmp_path: Path) -> None:
    """An independently encoded valid snapshot is accepted and exposes its published state."""
    data_dir = tmp_path / "db"
    data_dir.mkdir()
    (data_dir / "snapshot.dat").write_bytes(snapshot_bytes(1, [(b"alpha", b"one"), (b"beta", b"two")]))
    with Session(data_dir) as session:
        assert session.ready_sequence == 1
        reader = session.begin()
        assert get(session, reader, b"alpha") == b"one"
        assert get(session, reader, b"beta") == b"two"
        assert session.command(f"ROLLBACK {reader}") == "OK"


def test_complete_snapshot_oversized_key_is_fatal(tmp_path: Path) -> None:
    """A structurally complete checksummed snapshot row cannot exceed the decoded key limit."""
    data_dir = tmp_path / "db"
    data_dir.mkdir()
    (data_dir / "snapshot.dat").write_bytes(snapshot_bytes(1, [(b"k" * (MAX_KEY + 1), b"v")]))
    result = run_open(data_dir)
    assert result.returncode != 0
    assert "snapshot corruption" in result.stderr.lower()


def test_complete_snapshot_oversized_value_is_fatal(tmp_path: Path) -> None:
    """A structurally complete checksummed snapshot row cannot exceed the decoded value limit."""
    data_dir = tmp_path / "db"
    data_dir.mkdir()
    (data_dir / "snapshot.dat").write_bytes(snapshot_bytes(1, [(b"k", b"v" * (MAX_VALUE + 1))]))
    result = run_open(data_dir)
    assert result.returncode != 0
    assert "snapshot corruption" in result.stderr.lower()


def test_complete_snapshot_duplicate_key_is_fatal(tmp_path: Path) -> None:
    """Two independently encoded valid rows with the same key violate strict snapshot ordering."""
    data_dir = tmp_path / "db"
    data_dir.mkdir()
    (data_dir / "snapshot.dat").write_bytes(snapshot_bytes(1, [(b"dup", b"one"), (b"dup", b"two")]))
    result = run_open(data_dir)
    assert result.returncode != 0
    assert "snapshot corruption" in result.stderr.lower()


def test_health_rejects_missing_live_wal_path(tmp_path: Path) -> None:
    """HEALTH fails closed when a reachable durable-path invariant is broken while the engine is open."""
    data_dir = tmp_path / "db"
    session = Session(data_dir)
    try:
        (data_dir / "wal.log").unlink()
        response = session.command("HEALTH")
        assert response.startswith("ERR "), response
    finally:
        session.force_stop()


def test_cxx20_sources_and_public_abi_signatures_compile() -> None:
    """All native storage sources compile as C++20 and the documented extern-C signatures remain exact."""
    storage = PRODUCT_ROOT / "storage"
    cpp_files = sorted(str(path) for path in storage.glob("*.cpp"))
    assert cpp_files
    compile_sources = subprocess.run(
        ["g++", "-std=c++20", "-fsyntax-only", "-I", str(storage), *cpp_files],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert compile_sources.returncode == 0, compile_sources.stderr

    client = r'''
#include <cstddef>
#include <cstdint>
#include <type_traits>
#include "engine.hpp"
static_assert(std::is_same_v<decltype(&sv_open), void* (*)(const char*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_close), void (*)(void*)>);
static_assert(std::is_same_v<decltype(&sv_current_sequence), std::uint64_t (*)(void*)>);
static_assert(std::is_same_v<decltype(&sv_begin), std::uint64_t (*)(void*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_put), int (*)(void*, std::uint64_t, const char*, const char*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_del), int (*)(void*, std::uint64_t, const char*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_get), char* (*)(void*, std::uint64_t, const char*, int*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_scan), char* (*)(void*, std::uint64_t, const char*, int*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_commit), int (*)(void*, std::uint64_t, std::uint64_t*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_rollback), int (*)(void*, std::uint64_t, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_checkpoint), int (*)(void*, std::uint64_t*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_stats), char* (*)(void*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_health), char* (*)(void*, char*, std::size_t)>);
static_assert(std::is_same_v<decltype(&sv_free_string), void (*)(char*)>);
int main() { return 0; }
'''
    compile_abi = subprocess.run(
        ["g++", "-std=c++20", "-fsyntax-only", "-I", str(storage), "-x", "c++", "-"],
        input=client,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert compile_abi.returncode == 0, compile_abi.stderr


def test_ready_and_health_wire_shapes_are_exact(tmp_path: Path) -> None:
    """READY and HEALTH accept no undocumented trailing fields or alternate stable response shapes."""
    data_dir = tmp_path / "db"
    proc = subprocess.Popen(
        [str(BINARY), "--data-dir", str(data_dir)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        assert proc.stdout is not None
        assert re.fullmatch(r"READY 0", proc.stdout.readline().rstrip("\n"))
        assert proc.stdin is not None
        proc.stdin.write("HEALTH\n")
        proc.stdin.flush()
        health_line = proc.stdout.readline().rstrip("\n")
        assert re.fullmatch(
            r"HEALTH status=ok commit_seq=0 keys=0 active_tx=0 wal_bytes=0 snapshot=absent",
            health_line,
        )
        proc.stdin.write("QUIT\n")
        proc.stdin.flush()
        assert proc.stdout.readline().rstrip("\n") == "BYE"
        proc.wait(timeout=5)
        assert proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_unknown_transaction_errors_are_consistent_across_commands(tmp_path: Path) -> None:
    """Distinct transaction command families reject an unknown transaction without terminating the session."""
    with Session(tmp_path / "db") as session:
        commands = [
            "PUT 999 61 62",
            "DEL 999 61",
            "GET 999 61",
            "SCAN 999 61",
            "COMMIT 999",
            "ROLLBACK 999",
        ]
        for command in commands:
            assert session.command(command).startswith("ERR "), command
        tx_id = session.begin()
        assert session.command(f"ROLLBACK {tx_id}") == "OK"


def test_decoded_key_limit_is_consistent_across_commands(tmp_path: Path) -> None:
    """Distinct key-consuming command families reject the same decoded key overflow and keep the process alive."""
    oversized = (b"k" * (MAX_KEY + 1)).hex()
    with Session(tmp_path / "db") as session:
        tx_id = session.begin()
        assert session.command(f"PUT {tx_id} {oversized} 76").startswith("ERR ")
        assert session.command(f"DEL {tx_id} {oversized}").startswith("ERR ")
        assert session.command(f"GET {tx_id} {oversized}").startswith("ERR ")
        assert session.command(f"ROLLBACK {tx_id}") == "OK"
