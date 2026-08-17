"""Live-state checks for the event-time session window processor."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path("/app/sessions")
BIN = ROOT / "bin" / "run-sessions"
CONFIG = ROOT / "config" / "processor.json"
DATA = ROOT / "data"
OUT = ROOT / "output"
JOURNAL = DATA / "watermark.journal"
OPEN = DATA / "open_sessions.json"
SESSIONS = OUT / "sessions.jsonl"
LATE = OUT / "late.jsonl"
REJECTS = OUT / "rejects.jsonl"
WAREHOUSE = ROOT / "warehouse" / "click_ledger.jsonl"
HOLD = Path("/tests/fixtures")


def _clear_runtime() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for path in (JOURNAL, OPEN, SESSIONS, LATE, REJECTS):
        if path.exists():
            path.unlink()


def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(
        [str(BIN), *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"run-sessions failed rc={completed.returncode}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _journal_rows() -> list[dict]:
    return _load_jsonl(JOURNAL)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_config(gap: int = 30000, late: int = 10000, dur: int = 3600000) -> None:
    CONFIG.write_text(
        json.dumps(
            {
                "session_gap_ms": gap,
                "allowed_lateness_ms": late,
                "max_session_duration_ms": dur,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def _isolate():
    _write_config()
    _clear_runtime()
    yield
    _write_config()


def test_f2p_unknown_flag_leaves_journal_untouched() -> None:
    """Unknown flags must exit 2 without creating journal, opens, or side outputs."""
    completed = _run(["--not-a-real-flag"], check=False)
    assert completed.returncode == 2
    assert not JOURNAL.exists()
    assert not OPEN.exists()
    assert not SESSIONS.exists()
    assert not LATE.exists()
    assert not REJECTS.exists()


def test_f2p_unknown_flag_with_reset_does_not_clear_journal() -> None:
    """Unknown flags must not honor --reset-output against journal, opens, or outputs."""
    JOURNAL.write_text("keep\n", encoding="utf-8")
    OPEN.write_text('{"sessions":[]}\n', encoding="utf-8")
    SESSIONS.write_text("{}\n", encoding="utf-8")
    LATE.write_text("{}\n", encoding="utf-8")
    REJECTS.write_text("{}\n", encoding="utf-8")
    completed = _run(["--reset-output", "--not-a-real-flag"], check=False)
    assert completed.returncode == 2
    assert JOURNAL.read_text(encoding="utf-8") == "keep\n"
    assert OPEN.read_text(encoding="utf-8") == '{"sessions":[]}\n'
    assert SESSIONS.read_text(encoding="utf-8") == "{}\n"
    assert LATE.read_text(encoding="utf-8") == "{}\n"
    assert REJECTS.read_text(encoding="utf-8") == "{}\n"


def test_f2p_missing_source_does_not_create_journal() -> None:
    """Omitting --input/--feed/--empty-check must exit 2 without a journal file."""
    completed = _run([], check=False)
    assert completed.returncode == 2
    assert not JOURNAL.exists()


def test_f2p_empty_check_no_journal_file() -> None:
    """--empty-check must not create or append a watermark journal."""
    _run(["--empty-check"])
    assert SESSIONS.exists()
    assert LATE.exists()
    assert SESSIONS.read_text(encoding="utf-8") == ""
    assert LATE.read_text(encoding="utf-8") == ""
    assert not JOURNAL.exists()


def test_f2p_zero_event_file_no_journal_advance() -> None:
    """A zero-event --input file must not append watermark journal records."""
    _run(["--reset-output", "--input", str(HOLD / "empty.jsonl")])
    assert SESSIONS.read_text(encoding="utf-8") == ""
    assert LATE.read_text(encoding="utf-8") == ""
    assert not JOURNAL.exists()


def test_f2p_gap_close_half_open_end() -> None:
    """Event-time gap close must emit [1000, 35000) for the basic acme/u1 pair."""
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    closed = [
        row
        for row in _load_jsonl(SESSIONS)
        if row["tenant_id"] == "acme" and row["user_id"] == "u1"
    ]
    assert closed
    first = closed[0]
    assert first["start_ms"] == 1000
    assert first["end_ms"] == 35000
    assert first["event_ids"] == ["e1", "e2"]
    assert first["end_ms"] > first["start_ms"]


def test_f2p_input_sorts_before_gap_close() -> None:
    """--input must order by event time so a reversed file still gap-closes."""
    events = ROOT / "fixtures" / "_unsorted_gap.jsonl"
    events.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "z2",
                        "tenant_id": "acme",
                        "user_id": "u1",
                        "event_time_ms": 40000,
                        "payload": "later",
                    }
                ),
                json.dumps(
                    {
                        "event_id": "z1",
                        "tenant_id": "acme",
                        "user_id": "u1",
                        "event_time_ms": 1000,
                        "payload": "earlier",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _run(["--reset-output", "--input", str(events)])
    closed = _load_jsonl(SESSIONS)
    assert closed
    assert closed[0]["event_ids"] == ["z1"]
    assert closed[0]["end_ms"] == 31000


def test_f2p_event_count_matches_ids() -> None:
    """Closed session event_count must equal len(event_ids)."""
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    closed = [
        row
        for row in _load_jsonl(SESSIONS)
        if row["tenant_id"] == "acme" and row["user_id"] == "u1"
    ]
    assert closed
    assert closed[0]["event_count"] == len(closed[0]["event_ids"])
    assert closed[0]["event_count"] == 2


def test_f2p_tenant_isolation_same_user() -> None:
    """The same user_id under acme and beta must not share a session."""
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    open_snap = json.loads(OPEN.read_text(encoding="utf-8"))
    for row in _load_jsonl(SESSIONS):
        if row["user_id"] == "u1" and row["tenant_id"] == "acme":
            assert "e4" not in row["event_ids"]
    tenants = {row["tenant_id"] for row in open_snap["sessions"] if row["user_id"] == "u1"} | {
        row["tenant_id"] for row in _load_jsonl(SESSIONS) if row["user_id"] == "u1"
    }
    assert "acme" in tenants
    assert "beta" in tenants


def test_f2p_open_snapshot_keeps_beta_u1() -> None:
    """Open-session snapshot must keep beta/u1 as its own in-flight session."""
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    open_snap = json.loads(OPEN.read_text(encoding="utf-8"))
    beta = [
        row
        for row in open_snap["sessions"]
        if row["tenant_id"] == "beta" and row["user_id"] == "u1"
    ]
    assert beta
    assert beta[0]["event_ids"] == ["e4"]


def test_f2p_journal_seq_starts_at_one() -> None:
    """Journal seq values must start at 1 and increase by one per observation."""
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    rows = _journal_rows()
    assert rows
    seqs = [row["seq"] for row in rows]
    assert seqs == list(range(1, len(seqs) + 1))
    assert len(seqs) == 5


def test_f2p_journal_append_keeps_prefix() -> None:
    """A second run must append journal lines and leave the first prefix intact."""
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    first = _journal_rows()
    _run(["--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    second = _journal_rows()
    assert len(second) > len(first)
    assert second[: len(first)] == first


def test_f2p_journal_watermark_nondecreasing() -> None:
    """Journaled watermark_ms values must be non-decreasing across a late feed."""
    _run(["--reset-output", "--feed", str(HOLD / "feed_late.jsonl")])
    watermarks = [row["watermark_ms"] for row in _journal_rows()]
    assert watermarks
    assert watermarks == sorted(watermarks)


def test_p2p_feed_late_allowed_joins_open() -> None:
    """A late-but-allowed event must join the open session instead of late.jsonl."""
    _run(["--reset-output", "--feed", str(HOLD / "feed_late.jsonl")])
    open_snap = json.loads(OPEN.read_text(encoding="utf-8"))
    sess = next(row for row in open_snap["sessions"] if row["user_id"] == "u1")
    assert "f3" in sess["event_ids"]
    assert "f3" not in {row.get("event_id") for row in _load_jsonl(LATE)}


def test_f2p_feed_too_late_side_output() -> None:
    """A too-late event must land in late.jsonl with reason TOO_LATE."""
    _run(["--reset-output", "--feed", str(HOLD / "feed_late.jsonl")])
    late = _load_jsonl(LATE)
    assert any(row["event_id"] == "f4" and row["reason"] == "TOO_LATE" for row in late)
    open_snap = json.loads(OPEN.read_text(encoding="utf-8"))
    sess = next(row for row in open_snap["sessions"] if row["user_id"] == "u1")
    assert "f4" not in sess["event_ids"]


def test_f2p_late_record_schema() -> None:
    """Too-late side output must include the contract fields including watermark_ms."""
    _run(["--reset-output", "--feed", str(HOLD / "feed_late.jsonl")])
    late = [row for row in _load_jsonl(LATE) if row["event_id"] == "f4"]
    assert late
    row = late[0]
    assert set(row) >= {
        "event_id",
        "tenant_id",
        "user_id",
        "event_time_ms",
        "watermark_ms",
        "reason",
    }
    assert row["watermark_ms"] == 90000
    assert row["event_time_ms"] == 1000


def test_p2p_malformed_json_rejected() -> None:
    """Malformed JSON lines must fail closed into rejects.jsonl."""
    _run(
        [
            "--reset-output",
            "--feed",
            str(ROOT / "fixtures" / "sample_late_and_reject.jsonl"),
        ]
    )
    rejects = _load_jsonl(REJECTS)
    assert any(row["code"] == "REJECT_MALFORMED" for row in rejects)
    for row in rejects:
        assert "line_no" in row
        assert "detail" in row


def test_p2p_negative_event_time_rejected() -> None:
    """Negative event_time_ms must be rejected, not treated as late."""
    _run(
        [
            "--reset-output",
            "--feed",
            str(ROOT / "fixtures" / "sample_late_and_reject.jsonl"),
        ]
    )
    rejects = _load_jsonl(REJECTS)
    assert any(row.get("event_id") == "o4" and row["code"] == "REJECT_MALFORMED" for row in rejects)
    assert all(row.get("event_id") != "o4" for row in _load_jsonl(LATE))


def test_f2p_idempotent_session_digest() -> None:
    """The same clean baseline must reproduce the gap-closed session with identical bytes."""
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    closed = [
        row
        for row in _load_jsonl(SESSIONS)
        if row["tenant_id"] == "acme" and row["user_id"] == "u1"
    ]
    assert closed
    assert closed[0]["event_ids"] == ["e1", "e2"]
    digest_sessions = _sha256(SESSIONS)
    digest_late = _sha256(LATE)
    _clear_runtime()
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    assert _sha256(SESSIONS) == digest_sessions
    assert _sha256(LATE) == digest_late


def test_f2p_restart_extends_open_session() -> None:
    """Reloaded open-session state must accept a later in-gap event after restart."""
    _run(["--reset-output", "--feed", str(HOLD / "feed_late.jsonl")])
    more = ROOT / "fixtures" / "_restart_more.jsonl"
    more.write_text(
        json.dumps(
            {
                "event_id": "r1",
                "tenant_id": "acme",
                "user_id": "u1",
                "event_time_ms": 120000,
                "payload": "after-restart",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _run(["--feed", str(more)])
    open_after = json.loads(OPEN.read_text(encoding="utf-8"))
    ids = next(row["event_ids"] for row in open_after["sessions"] if row["user_id"] == "u1")
    assert "r1" in ids
    assert "f1" in ids
    seqs = [row["seq"] for row in _journal_rows()]
    assert seqs == list(range(1, len(seqs) + 1))
    assert seqs[-1] > 5


def test_f2p_restart_watermark_nondecreasing() -> None:
    """A restarted feed must not journal a watermark below the previous last value."""
    _run(["--reset-output", "--feed", str(HOLD / "feed_late.jsonl")])
    before = _journal_rows()
    last_wm = before[-1]["watermark_ms"]
    more = ROOT / "fixtures" / "_restart_wm.jsonl"
    more.write_text(
        json.dumps(
            {
                "event_id": "r2",
                "tenant_id": "acme",
                "user_id": "u1",
                "event_time_ms": 130000,
                "payload": "after-restart-wm",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _run(["--feed", str(more)])
    after = _journal_rows()
    assert after[: len(before)] == before
    assert after[-1]["watermark_ms"] >= last_wm


def test_f2p_config_gap_honored() -> None:
    """processor.json session_gap_ms must drive event-time gap closes."""
    _write_config(gap=5_000, late=10_000, dur=3_600_000)
    events = ROOT / "fixtures" / "_gap_probe.jsonl"
    events.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "g1",
                        "tenant_id": "acme",
                        "user_id": "u1",
                        "event_time_ms": 1000,
                        "payload": "a",
                    }
                ),
                json.dumps(
                    {
                        "event_id": "g2",
                        "tenant_id": "acme",
                        "user_id": "u1",
                        "event_time_ms": 7000,
                        "payload": "b",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _run(["--reset-output", "--input", str(events)])
    sessions = _load_jsonl(SESSIONS)
    assert sessions
    assert sessions[0]["end_ms"] == 6000


def test_p2p_config_max_duration_close() -> None:
    """max_session_duration_ms must close before accepting an out-of-span event."""
    _write_config(gap=1_000_000, late=10_000, dur=10_000)
    events = ROOT / "fixtures" / "_dur.jsonl"
    events.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "d1",
                        "tenant_id": "acme",
                        "user_id": "u1",
                        "event_time_ms": 0,
                        "payload": "a",
                    }
                ),
                json.dumps(
                    {
                        "event_id": "d2",
                        "tenant_id": "acme",
                        "user_id": "u1",
                        "event_time_ms": 15000,
                        "payload": "b",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _run(["--reset-output", "--input", str(events)])
    sessions = _load_jsonl(SESSIONS)
    assert sessions
    assert sessions[0]["end_ms"] == 10000
    assert sessions[0]["event_ids"] == ["d1"]


def test_f2p_config_lateness_marks_too_late() -> None:
    """Shrinking allowed_lateness_ms must classify a behind event as TOO_LATE."""
    _write_config(gap=30000, late=10000, dur=3600000)
    _run(["--reset-output", "--feed", str(HOLD / "lateness_probe.jsonl")])
    late = _load_jsonl(LATE)
    assert any(row["event_id"] == "l2" and row["reason"] == "TOO_LATE" for row in late)


def test_f2p_holdout_gap_and_tenant() -> None:
    """Holdout input must gap-close alice, watermark-close idle bob, and isolate other/alice."""
    _run(["--reset-output", "--input", str(HOLD / "holdout_sessions.jsonl")])
    sessions = _load_jsonl(SESSIONS)
    hold_alice = [row for row in sessions if row["tenant_id"] == "hold" and row["user_id"] == "alice"]
    assert hold_alice
    assert hold_alice[0]["event_ids"] == ["h1", "h2", "h3"]
    assert hold_alice[0]["end_ms"] == 55000
    open_snap = json.loads(OPEN.read_text(encoding="utf-8"))
    all_rows = list(open_snap["sessions"]) + sessions
    other = [
        row for row in all_rows if row.get("tenant_id") == "other" and row.get("user_id") == "alice"
    ]
    assert other
    assert other[0]["event_ids"] == ["h6"]
    bob = [row for row in sessions if row["tenant_id"] == "hold" and row["user_id"] == "bob"]
    assert bob
    assert bob[0]["event_ids"] == ["h4"]
    assert bob[0]["end_ms"] == 45000


def test_p2p_input_tie_break_stable() -> None:
    """--input must tie-break equal event times so a permutation is a no-op."""
    _run(["--reset-output", "--input", str(HOLD / "tie_break.jsonl")])
    open1 = json.loads(OPEN.read_text(encoding="utf-8"))
    permuted = HOLD / "_tie_perm.jsonl"
    rows = (HOLD / "tie_break.jsonl").read_text(encoding="utf-8").splitlines()
    permuted.write_text("\n".join(reversed(rows)) + "\n", encoding="utf-8")
    _clear_runtime()
    _run(["--reset-output", "--input", str(permuted)])
    open2 = json.loads(OPEN.read_text(encoding="utf-8"))

    def by_user(snap: dict) -> dict:
        return {row["user_id"]: row["event_ids"] for row in snap["sessions"]}

    assert by_user(open1) == by_user(open2)


def test_f2p_feed_preserves_arrival_order() -> None:
    """--feed must keep file order so an earlier timestamp after a high anchor is too late."""
    _run(["--reset-output", "--feed", str(HOLD / "feed_order.jsonl")])
    late = _load_jsonl(LATE)
    assert any(row["event_id"] == "p1" and row["reason"] == "TOO_LATE" for row in late)
    open_snap = json.loads(OPEN.read_text(encoding="utf-8"))
    sess = next(row for row in open_snap["sessions"] if row["user_id"] == "u1")
    assert sess["event_ids"] == ["p2"]


def test_f2p_reset_output_keeps_journal() -> None:
    """--reset-output may truncate side files but must leave journal and in-flight sessions."""
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    before = JOURNAL.read_text(encoding="utf-8")
    open_before = OPEN.read_text(encoding="utf-8")
    assert before.strip()
    assert open_before.strip()
    _run(["--reset-output", "--empty-check"])
    assert JOURNAL.read_text(encoding="utf-8") == before
    assert OPEN.read_text(encoding="utf-8") == open_before
    assert SESSIONS.read_text(encoding="utf-8") == ""
    assert LATE.read_text(encoding="utf-8") == ""


def test_f2p_watermark_formula_in_journal() -> None:
    """The first journaled watermark must be max_observed minus allowed lateness."""
    _run(["--reset-output", "--feed", str(HOLD / "feed_late.jsonl")])
    first = _journal_rows()[0]
    assert first["max_observed_event_time_ms"] == 80000
    assert first["watermark_ms"] == 70000
    assert first["seq"] == 1


def test_f2p_closed_session_schema() -> None:
    """Closed session lines must include the contract fields and a positive interval."""
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    rows = _load_jsonl(SESSIONS)
    assert rows
    row = rows[0]
    assert set(row) >= {
        "tenant_id",
        "user_id",
        "start_ms",
        "end_ms",
        "event_ids",
        "event_count",
    }
    assert row["end_ms"] > row["start_ms"]


def test_p2p_warehouse_at_least_10k() -> None:
    """Inherited click ledger must remain a production-scale dump."""
    assert WAREHOUSE.is_file()
    lines = [line for line in WAREHOUSE.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 10000


def test_p2p_warehouse_untouched_after_run() -> None:
    """A processor run must not rewrite the warehouse click dump."""
    before = _sha256(WAREHOUSE)
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    assert _sha256(WAREHOUSE) == before


def test_p2p_bin_and_contract_present() -> None:
    """Operator CLI and binding contract must remain at the documented paths."""
    assert BIN.is_file()
    contract = ROOT / "docs" / "session-contract.md"
    assert contract.is_file()
    text = contract.read_text(encoding="utf-8")
    assert "watermark_ms = max_observed_event_time_ms - allowed_lateness_ms" in text


def test_p2p_python_cli_entrypoint() -> None:
    """run-sessions must keep launching the Python processor."""
    text = BIN.read_text(encoding="utf-8")
    assert "python3" in text


def test_p2p_output_paths() -> None:
    """Documented output paths must be writable under /app/sessions/output."""
    _run(["--empty-check"])
    assert SESSIONS.parent == ROOT / "output"
    assert LATE.parent == ROOT / "output"
    assert REJECTS.parent == ROOT / "output"
    assert SESSIONS.exists()
    assert LATE.exists()


def test_p2p_config_keys() -> None:
    """processor.json must keep the three session knobs."""
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert set(raw) >= {"session_gap_ms", "allowed_lateness_ms", "max_session_duration_ms"}
    assert int(raw["session_gap_ms"]) > 0
    assert int(raw["allowed_lateness_ms"]) > 0
    assert int(raw["max_session_duration_ms"]) > 0
