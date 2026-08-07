"""Idempotency, atomicity, twin-post, and audit transaction checks."""

from __future__ import annotations

import os
import signal
import subprocess
import time

from conftest import CLI, cli_environment, connection, run_cli, scalar


def initiate(
    request: str,
    wire: str,
    debit: str = "ACC-D1",
    credit: str = "ACC-C1",
    amount: int = 10000,
    initiator: str = "OP-A1",
) -> str:
    """Create one initiated wire and return its response."""
    result = run_cli(
        "INITIATE", request, wire, debit, credit, amount, initiator
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_identical_retry_returns_byte_exact_result_once() -> None:
    """An exact retry must replay the stored line without another audit event."""
    first = initiate("REQ-I01", "WR-I01")
    second = run_cli(
        "INITIATE", "REQ-I01", "WR-I01", "ACC-D1", "ACC-C1", "10000", "OP-A1"
    )
    assert second.returncode == 0
    assert second.stdout == first
    assert scalar("SELECT count(*) FROM wire_request") == 1
    assert scalar("SELECT count(*) FROM audit_event") == 1


def test_request_id_reuse_with_one_changed_argument_conflicts() -> None:
    """A reused request ID must compare every parsed command argument."""
    initiate("REQ-I02", "WR-I02")
    first = run_cli("APPROVE", "REQ-I03", "WR-I02", "1", "OP-A2")
    conflict = run_cli("APPROVE", "REQ-I03", "WR-I02", "1", "OP-B1")
    assert first.returncode == 0
    assert conflict.returncode == 1
    assert conflict.stdout == (
        "ERR|request=REQ-I03|command=APPROVE|code=REQUEST_CONFLICT\n"
    )
    assert str(scalar("SELECT approver_id FROM wire_request")).strip() == "OP-A2"
    assert scalar("SELECT count(*) FROM request_record") == 2


def test_business_rejection_is_permanent_and_replayable() -> None:
    """The first completed stale request must remain its permanent result."""
    initiate("REQ-I04", "WR-I04")
    assert run_cli("APPROVE", "REQ-I05", "WR-I04", "1", "OP-A2").returncode == 0
    stale = run_cli("RELEASE", "REQ-I06", "WR-I04", "1")
    replay = run_cli("RELEASE", "REQ-I06", "WR-I04", "1")
    assert stale.returncode == 1
    assert replay.returncode == 0
    assert stale.stdout == replay.stdout
    assert "code=STALE_REVISION" in stale.stdout
    assert scalar("SELECT count(*) FROM audit_event") == 2


def test_release_posts_twin_ledger_and_updates_both_balances() -> None:
    """Accepted RELEASE must debit one side and credit the other atomically."""
    initiate("REQ-T01", "WR-T01", amount=25000)
    assert run_cli("APPROVE", "REQ-T02", "WR-T01", "1", "OP-A2").returncode == 0
    released = run_cli("RELEASE", "REQ-T03", "WR-T01", "2")
    assert released.returncode == 0
    assert "|debit=000000975000|credit=000000125000|" in released.stdout
    with connection() as conn:
        sides = [
            (str(row[0]).strip(), row[1], str(row[2]).strip())
            for row in conn.execute(
                "SELECT side, amount_cents, account_id FROM ledger_entry "
                "ORDER BY side"
            )
        ]
    assert sides == [
        ("CREDIT", 25000, "ACC-C1"),
        ("DEBIT", 25000, "ACC-D1"),
    ]
    assert scalar(
        "SELECT balance_cents FROM wire_account WHERE account_id='ACC-D1'"
    ) == 975000
    assert scalar(
        "SELECT balance_cents FROM wire_account WHERE account_id='ACC-C1'"
    ) == 125000


def test_rejections_and_replays_leave_a_gap_free_audit() -> None:
    """Only accepted mutations may consume the serialized audit counter."""
    first = initiate("REQ-A11", "WR-A11")
    rejected = run_cli("APPROVE", "REQ-A12", "WR-A11", "1", "OP-ZZ")
    replay = run_cli(
        "INITIATE", "REQ-A11", "WR-A11", "ACC-D1", "ACC-C1", "10000", "OP-A1"
    )
    cancelled = run_cli("CANCEL", "REQ-A13", "WR-A11", "1")
    assert first == replay.stdout
    assert rejected.returncode == 1
    assert cancelled.returncode == 0
    with connection() as conn:
        sequences = [
            row[0]
            for row in conn.execute(
                "SELECT audit_sequence FROM audit_event ORDER BY audit_sequence"
            )
        ]
    assert sequences == [1, 2]
    assert scalar("SELECT next_value FROM audit_counter") == 3


def test_process_termination_rolls_back_request_state_and_audit() -> None:
    """Killing the client during audit insertion must expose no partial wire."""
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
        [
            str(CLI),
            "INITIATE",
            "REQ-K01",
            "WR-K01",
            "ACC-D1",
            "ACC-C1",
            "10000",
            "OP-A1",
        ],
        cwd="/app/wire",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=cli_environment(),
    )
    deadline = time.monotonic() + 10
    sleeping = False
    while time.monotonic() < deadline:
        with connection() as conn:
            sleeping = bool(
                conn.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                    "WHERE query LIKE 'INSERT INTO audit_event%')"
                ).fetchone()[0]
            )
        if sleeping:
            break
        time.sleep(0.1)
    assert sleeping
    os.kill(process.pid, signal.SIGKILL)
    process.wait(timeout=5)

    with connection() as conn:
        conn.execute("DROP TRIGGER verifier_pause ON audit_event")
        conn.execute("DROP FUNCTION verifier_pause_audit()")
    assert scalar("SELECT count(*) FROM wire_request") == 0
    assert scalar("SELECT count(*) FROM request_record") == 0
    assert scalar("SELECT count(*) FROM audit_event") == 0
    assert scalar("SELECT next_value FROM audit_counter") == 1
