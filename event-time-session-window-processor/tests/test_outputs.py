"""Semantic live-state checks for the event-time session window processor."""
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
HOLD = Path("/tests/fixtures")


def _clear_runtime() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for p in (JOURNAL, OPEN, SESSIONS, LATE, REJECTS):
        if p.exists():
            p.unlink()


def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    cp = subprocess.run(
        [str(BIN), *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and cp.returncode != 0:
        raise AssertionError(
            f"run-sessions failed rc={cp.returncode}\nstdout={cp.stdout}\nstderr={cp.stderr}"
        )
    return cp


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


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


def test_cli_rejects_unknown_flags_before_state_touch():
    JOURNAL.write_text("keep\n", encoding="utf-8")
    before = JOURNAL.read_text(encoding="utf-8")
    cp = _run(["--not-a-real-flag"], check=False)
    assert cp.returncode == 2
    assert JOURNAL.read_text(encoding="utf-8") == before


def test_empty_check_no_watermark_advance():
    _run(["--empty-check"])
    assert SESSIONS.exists()
    assert LATE.exists()
    assert SESSIONS.read_text(encoding="utf-8") == ""
    assert LATE.read_text(encoding="utf-8") == ""
    assert not JOURNAL.exists() or JOURNAL.read_text(encoding="utf-8").strip() == ""


def test_basic_gap_close_and_half_open_end():
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    sessions = _load_jsonl(SESSIONS)
    closed = [s for s in sessions if s["tenant_id"] == "acme" and s["user_id"] == "u1"]
    assert closed, "expected a closed acme/u1 session after gap"
    s0 = closed[0]
    assert s0["start_ms"] == 1000
    assert s0["end_ms"] == 35000
    assert s0["event_ids"] == ["e1", "e2"]
    assert s0["event_count"] == 2
    assert s0["end_ms"] > s0["start_ms"]


def test_multi_tenant_isolation_same_user_id():
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    open_snap = json.loads(OPEN.read_text(encoding="utf-8"))
    for s in open_snap["sessions"]:
        assert s["tenant_id"] in {"acme", "beta"}
    for s in _load_jsonl(SESSIONS):
        assert s["tenant_id"] in {"acme", "beta"}
        if s["user_id"] == "u1" and s["tenant_id"] == "acme":
            assert "e4" not in s["event_ids"]
    tenants_for_u1 = {
        s["tenant_id"]
        for s in open_snap["sessions"]
        if s["user_id"] == "u1"
    } | {
        s["tenant_id"]
        for s in _load_jsonl(SESSIONS)
        if s["user_id"] == "u1"
    }
    assert "acme" in tenants_for_u1
    assert "beta" in tenants_for_u1


def test_watermark_journal_monotonic_and_append_only():
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    lines1 = [json.loads(l) for l in JOURNAL.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert lines1, "journal must record watermark advances"
    seqs = [r["seq"] for r in lines1]
    assert seqs == list(range(1, len(seqs) + 1))
    wms = [r["watermark_ms"] for r in lines1]
    assert wms == sorted(wms)

    _run(["--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    lines2 = [json.loads(l) for l in JOURNAL.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines2) > len(lines1)
    assert lines2[: len(lines1)] == lines1


def test_feed_late_allowed_and_too_late_side_output():
    _run(["--reset-output", "--feed", str(HOLD / "feed_late.jsonl")])
    late = _load_jsonl(LATE)
    assert any(r["event_id"] == "f4" and r["reason"] == "TOO_LATE" for r in late)
    for r in late:
        assert set(r) >= {
            "event_id",
            "tenant_id",
            "user_id",
            "event_time_ms",
            "watermark_ms",
            "reason",
        }
    open_snap = json.loads(OPEN.read_text(encoding="utf-8"))
    sess = next(s for s in open_snap["sessions"] if s["user_id"] == "u1")
    assert "f3" in sess["event_ids"]
    assert "f4" not in sess["event_ids"]


def test_rejects_malformed_without_updating_sessions():
    _run(
        [
            "--reset-output",
            "--feed",
            str(ROOT / "fixtures" / "sample_late_and_reject.jsonl"),
        ]
    )
    rejects = _load_jsonl(REJECTS)
    assert any(r["code"] == "REJECT_MALFORMED" for r in rejects)
    for r in rejects:
        assert "line_no" in r and "detail" in r


def test_idempotent_digests_from_clean_baseline():
    _clear_runtime()
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    d1_s = _sha256(SESSIONS)
    d1_l = _sha256(LATE)
    _clear_runtime()
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    assert _sha256(SESSIONS) == d1_s
    assert _sha256(LATE) == d1_l


def test_restart_restores_open_sessions_and_watermark():
    _run(["--reset-output", "--feed", str(HOLD / "feed_late.jsonl")])
    journal_before = JOURNAL.read_text(encoding="utf-8")
    last_wm = [json.loads(l)["watermark_ms"] for l in journal_before.splitlines() if l.strip()][-1]

    for p in (SESSIONS, LATE, REJECTS):
        if p.exists():
            p.unlink()

    more = ROOT / "fixtures" / "_restart_more.jsonl"
    more.write_text(
        json.dumps(
            {
                "event_id": "r1",
                "tenant_id": "acme",
                "user_id": "u1",
                # Within gap of last event from feed_late (110000) so the open
                # session is extended rather than closed-and-replaced.
                "event_time_ms": 120000,
                "payload": "after-restart",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _run(["--feed", str(more)])
    open_after = json.loads(OPEN.read_text(encoding="utf-8"))
    journal_after = [
        json.loads(l) for l in JOURNAL.read_text(encoding="utf-8").splitlines() if l.strip()
    ]
    assert journal_after[-1]["watermark_ms"] >= last_wm
    ids = next(s["event_ids"] for s in open_after["sessions"] if s["user_id"] == "u1")
    assert "r1" in ids
    assert "f1" in ids


def test_config_gap_is_honored():
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
    assert sessions, "gap=5000 should close between 1000 and 7000"
    assert sessions[0]["end_ms"] == 6000


def test_holdout_sessions_semantics():
    _run(["--reset-output", "--input", str(HOLD / "holdout_sessions.jsonl")])
    sessions = _load_jsonl(SESSIONS)
    hold_alice = [s for s in sessions if s["tenant_id"] == "hold" and s["user_id"] == "alice"]
    assert hold_alice
    assert hold_alice[0]["event_ids"] == ["h1", "h2", "h3"]
    assert hold_alice[0]["end_ms"] == 55000
    open_snap = json.loads(OPEN.read_text(encoding="utf-8"))
    all_alice = list(open_snap["sessions"]) + _load_jsonl(SESSIONS)
    tenants = {s["tenant_id"] for s in all_alice if s.get("user_id") == "alice"}
    assert "other" in tenants
    other_rows = [s for s in all_alice if s.get("tenant_id") == "other" and s.get("user_id") == "alice"]
    assert other_rows
    assert other_rows[0]["event_ids"] == ["h6"]
    assert "h1" not in other_rows[0]["event_ids"]


def test_tie_break_order_stable_digest():
    _run(["--reset-output", "--input", str(HOLD / "tie_break.jsonl")])
    open1 = json.loads(OPEN.read_text(encoding="utf-8"))
    permuted = HOLD / "_tie_perm.jsonl"
    rows = (HOLD / "tie_break.jsonl").read_text(encoding="utf-8").splitlines()
    permuted.write_text("\n".join(reversed(rows)) + "\n", encoding="utf-8")
    _clear_runtime()
    _run(["--reset-output", "--input", str(permuted)])
    open2 = json.loads(OPEN.read_text(encoding="utf-8"))

    def by_user(snap: dict) -> dict:
        return {s["user_id"]: s["event_ids"] for s in snap["sessions"]}

    assert by_user(open1) == by_user(open2)


def test_max_duration_closes_session():
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


def test_contract_present_and_binding_formula_documented():
    contract = ROOT / "docs" / "session-contract.md"
    assert contract.is_file()
    text = contract.read_text(encoding="utf-8")
    assert "watermark_ms = max_observed_event_time_ms - allowed_lateness_ms" in text


def test_no_sleep_based_windowing_in_processor_source():
    src = (ROOT / "src" / "processor.py").read_text(encoding="utf-8")
    assert "time.sleep" not in src
    assert "sleep(" not in src


def test_journal_and_open_state_are_valid_after_run():
    _run(["--reset-output", "--input", str(ROOT / "fixtures" / "sample_basic.jsonl")])
    for line in JOURNAL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            json.loads(line)
    snap = json.loads(OPEN.read_text(encoding="utf-8"))
    assert "sessions" in snap
