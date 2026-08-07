"""Idempotency, atomicity, overlap, and audit transaction checks."""

from __future__ import annotations

import os
import signal
import subprocess
import time

from conftest import CLI, cli_environment, connection, run_cli, scalar


def open_order(request: str, order: str, priority: int = 2) -> str:
    """Create one transport work order and return its response."""
    result = run_cli("OPEN", request, order, "TRANSPORT", priority)
    assert result.returncode == 0, result.stderr
    return result.stdout


def reserve(
    request: str,
    order: str,
    bay: str,
    technician: str,
    start: int,
    end: int,
) -> subprocess.CompletedProcess[str]:
    """Reserve a revision-one transport order through the public command."""
    return run_cli(
        "RESERVE", request, order, "1", bay, technician, start, end
    )


def test_identical_retry_returns_byte_exact_result_once() -> None:
    """An exact retry must replay the stored line without another audit event."""
    first = open_order("REQ-I01", "WO-I01")
    second = run_cli("OPEN", "REQ-I01", "WO-I01", "TRANSPORT", "2")
    assert second.returncode == 0
    assert second.stdout == first
    assert scalar("SELECT count(*) FROM work_order") == 1
    assert scalar("SELECT count(*) FROM audit_event") == 1


def test_request_id_reuse_with_one_changed_argument_conflicts() -> None:
    """A reused request ID must compare every parsed command argument."""
    open_order("REQ-I02", "WO-I02")
    first = reserve("REQ-I03", "WO-I02", "BAY-T1", "TECH-T1", 100, 200)
    conflict = run_cli(
        "RESERVE", "REQ-I03", "WO-I02", "1", "BAY-T1", "TECH-T1", "100", "201"
    )
    assert first.returncode == 0
    assert conflict.returncode == 1
    assert conflict.stdout == (
        "ERR|request=REQ-I03|command=RESERVE|code=REQUEST_CONFLICT\n"
    )
    assert scalar("SELECT end_tick FROM booking") == 200
    assert scalar("SELECT count(*) FROM request_record") == 2


def test_business_rejection_is_permanent_and_replayable() -> None:
    """The first completed stale request must remain its permanent result."""
    open_order("REQ-I04", "WO-I04")
    assert reserve("REQ-I05", "WO-I04", "BAY-T1", "TECH-T1", 60, 120).returncode == 0
    stale = run_cli("START", "REQ-I06", "WO-I04", "1")
    replay = run_cli("START", "REQ-I06", "WO-I04", "1")
    assert stale.returncode == 1
    assert replay.returncode == 0
    assert stale.stdout == replay.stdout
    assert "code=STALE_REVISION" in stale.stdout
    assert scalar("SELECT count(*) FROM audit_event") == 2


def test_failed_move_preserves_every_booking_field() -> None:
    """Replacement validation must finish before any existing slot is changed."""
    open_order("REQ-M01", "WO-M01")
    assert reserve("REQ-M02", "WO-M01", "BAY-T1", "TECH-T1", 100, 200).returncode == 0
    with connection() as conn:
        before = conn.execute(
            "SELECT bay_id, technician_id, start_tick, end_tick, revision, "
            "policy_id, shift_code, supervision_level, capacity_percent "
            "FROM booking"
        ).fetchone()

    failed = run_cli(
        "MOVE", "REQ-M03", "WO-M01", "2", "BAY-G1", "TECH-G1", "300", "350"
    )
    with connection() as conn:
        after = conn.execute(
            "SELECT bay_id, technician_id, start_tick, end_tick, revision, "
            "policy_id, shift_code, supervision_level, capacity_percent "
            "FROM booking"
        ).fetchone()
    assert failed.returncode == 1
    assert "code=INCOMPATIBLE_RESOURCE" in failed.stdout
    assert after == before
    assert scalar("SELECT revision FROM work_order") == 2


def test_adjacent_half_open_slots_do_not_conflict() -> None:
    """One slot ending exactly as another starts must be accepted."""
    open_order("REQ-H01", "WO-H01")
    open_order("REQ-H02", "WO-H02")
    first = reserve("REQ-H03", "WO-H01", "BAY-T1", "TECH-T1", 100, 200)
    adjacent = reserve("REQ-H04", "WO-H02", "BAY-T1", "TECH-T1", 200, 300)
    assert first.returncode == adjacent.returncode == 0
    assert scalar("SELECT count(*) FROM booking") == 2


def test_conflict_checks_bay_and_technician_independently() -> None:
    """Either shared resource must reject an overlapping second booking."""
    open_order("REQ-H05", "WO-H03")
    open_order("REQ-H06", "WO-H04")
    open_order("REQ-H07", "WO-H05")
    assert reserve("REQ-H08", "WO-H03", "BAY-T1", "TECH-T1", 300, 400).returncode == 0
    same_bay = reserve("REQ-H09", "WO-H04", "BAY-T1", "TECH-T2", 350, 450)
    same_tech = reserve("REQ-H10", "WO-H05", "BAY-T2", "TECH-T1", 350, 450)
    assert "code=RESOURCE_BUSY" in same_bay.stdout
    assert "code=RESOURCE_BUSY" in same_tech.stdout
    assert scalar("SELECT count(*) FROM booking") == 1


def test_rejections_and_replays_leave_a_gap_free_audit() -> None:
    """Only accepted mutations may consume the serialized audit counter."""
    first = open_order("REQ-A11", "WO-A11")
    rejected = reserve("REQ-A12", "WO-A11", "BAY-Z9", "TECH-Z9", 0, 10)
    replay = run_cli("OPEN", "REQ-A11", "WO-A11", "TRANSPORT", "2")
    cancelled = run_cli("CANCEL", "REQ-A13", "WO-A11", "1")
    assert first == replay.stdout
    assert rejected.returncode == 1
    assert cancelled.returncode == 0
    with connection() as conn:
        sequences = [row[0] for row in conn.execute(
            "SELECT audit_sequence FROM audit_event ORDER BY audit_sequence"
        )]
    assert sequences == [1, 2]
    assert scalar("SELECT next_value FROM audit_counter") == 3


def test_process_termination_rolls_back_request_state_and_audit() -> None:
    """Killing the client during audit insertion must expose no partial order."""
    with connection() as conn:
        conn.execute(
            "CREATE OR REPLACE FUNCTION verifier_pause_audit() RETURNS trigger "
            "LANGUAGE plpgsql AS $$ BEGIN PERFORM pg_sleep(20); RETURN NEW; END $$"
        )
        conn.execute(
            "CREATE TRIGGER verifier_pause BEFORE INSERT ON audit_event "
            "FOR EACH ROW EXECUTE FUNCTION verifier_pause_audit()"
        )

    process = subprocess.Popen(
        [str(CLI), "OPEN", "REQ-K01", "WO-K01", "TRANSPORT", "2"],
        cwd="/app/workshop",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=cli_environment(),
    )
    deadline = time.monotonic() + 10
    sleeping = False
    while time.monotonic() < deadline:
        with connection() as conn:
            sleeping = bool(conn.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                "WHERE query LIKE 'INSERT INTO audit_event%')"
            ).fetchone()[0])
        if sleeping:
            break
        time.sleep(0.1)
    assert sleeping
    os.kill(process.pid, signal.SIGKILL)
    process.wait(timeout=5)

    with connection() as conn:
        conn.execute("DROP TRIGGER verifier_pause ON audit_event")
        conn.execute("DROP FUNCTION verifier_pause_audit()")
    assert scalar("SELECT count(*) FROM work_order") == 0
    assert scalar("SELECT count(*) FROM request_record") == 0
    assert scalar("SELECT count(*) FROM audit_event") == 0
    assert scalar("SELECT next_value FROM audit_counter") == 1
