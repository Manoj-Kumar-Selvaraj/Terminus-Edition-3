"""Public command, state-machine, and build-boundary checks."""

import subprocess

from conftest import connection, run_cli, scalar


def test_native_application_builds_and_reaches_the_database() -> None:
    """The submitted COBOL command must build and use the live schema."""
    dynamic = subprocess.run(
        ["readelf", "-d", "/app/workshop/bin/workshop-terminal"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "libcob.so" in dynamic
    assert "libocesql.so" in dynamic
    assert "libpq.so" in dynamic
    health = run_cli("HEALTH")
    assert health.returncode == 0
    assert health.stdout == "HEALTH|database=READY|schema=1\n"


def test_usage_errors_are_rejected_before_database_work() -> None:
    """Malformed commands must return exit 2 on stderr and write no rows."""
    missing = run_cli("RESERVE", "REQ-U01", "WO-U01")
    signed_tick = run_cli(
        "RESERVE", "REQ-U02", "WO-U01", "1", "BAY-T1", "TECH-T1", "+1", "20"
    )
    assert missing.returncode == 2
    assert missing.stdout == ""
    assert "code=USAGE" in missing.stderr
    assert signed_tick.returncode == 2
    assert scalar("SELECT count(*) FROM request_record") == 0


def test_open_status_start_and_complete_follow_public_state_machine() -> None:
    """A normal order must advance once per accepted lifecycle command."""
    opened = run_cli("OPEN", "REQ-L01", "WO-L01", "TRANSPORT", "2")
    reserved = run_cli(
        "RESERVE", "REQ-L02", "WO-L01", "1", "BAY-T1", "TECH-T1", "60", "180"
    )
    started = run_cli("START", "REQ-L03", "WO-L01", "2")
    completed = run_cli("COMPLETE", "REQ-L04", "WO-L01", "3")
    status = run_cli("STATUS", "WO-L01")

    assert opened.stdout.endswith("|revision=000001|state=OPEN|audit=0000000001\n")
    assert reserved.stdout.endswith("|revision=000002|state=RESERVED|audit=0000000002\n")
    assert started.stdout.endswith("|revision=000003|state=STARTED|audit=0000000003\n")
    assert completed.stdout.endswith("|revision=000004|state=COMPLETED|audit=0000000004\n")
    assert "|state=COMPLETED|booking=NONE|bay=NONE|" in status.stdout
    assert str(scalar("SELECT state FROM booking")).strip() == "COMPLETED"


def test_cancel_handles_open_and_reserved_orders_without_orphans() -> None:
    """Cancellation must work in both allowed states and close active bookings."""
    assert run_cli("OPEN", "REQ-C01", "WO-C01", "RADIO", "1").returncode == 0
    cancelled_open = run_cli("CANCEL", "REQ-C02", "WO-C01", "1")
    assert "|booking=NONE|revision=000002|state=CANCELLED|" in cancelled_open.stdout

    assert run_cli("OPEN", "REQ-C03", "WO-C02", "RADIO", "1").returncode == 0
    assert run_cli(
        "RESERVE", "REQ-C04", "WO-C02", "1", "BAY-R1", "TECH-R1", "0", "60"
    ).returncode == 0
    cancelled_reserved = run_cli("CANCEL", "REQ-C05", "WO-C02", "2")
    assert "|revision=000003|state=CANCELLED|" in cancelled_reserved.stdout
    assert scalar(
        "SELECT count(*) FROM booking WHERE state IN ('RESERVED', 'STARTED')"
    ) == 0


def test_rejection_precedence_is_stable_and_recorded() -> None:
    """Unknown order must win over later resource, revision, and window checks."""
    result = run_cli(
        "RESERVE", "REQ-P01", "WO-NOPE", "999", "BAY-Z9", "TECH-Z9", "9", "1"
    )
    assert result.returncode == 1
    assert result.stdout == "ERR|request=REQ-P01|command=RESERVE|code=UNKNOWN_ORDER\n"
    assert scalar("SELECT count(*) FROM request_record") == 1
    assert scalar("SELECT count(*) FROM audit_event") == 0


def test_incompatible_and_inactive_resources_fail_closed() -> None:
    """Class mismatch and inactive resources must not create a booking."""
    assert run_cli("OPEN", "REQ-R01", "WO-R01", "MEDICAL", "2").returncode == 0
    wrong_class = run_cli(
        "RESERVE", "REQ-R02", "WO-R01", "1", "BAY-T1", "TECH-M1", "0", "60"
    )
    assert "code=INCOMPATIBLE_RESOURCE" in wrong_class.stdout

    with connection() as conn:
        conn.execute("UPDATE workshop_bay SET active=false WHERE bay_id='BAY-M1'")
    inactive = run_cli(
        "RESERVE", "REQ-R03", "WO-R01", "1", "BAY-M1", "TECH-M1", "0", "60"
    )
    assert "code=UNKNOWN_RESOURCE" in inactive.stdout
    assert scalar("SELECT count(*) FROM booking") == 0
