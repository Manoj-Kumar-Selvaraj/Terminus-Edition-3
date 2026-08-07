"""Public command, state-machine, and build-boundary checks."""

import subprocess

from conftest import run_cli, scalar


def test_native_application_builds_and_reaches_the_database() -> None:
    """The submitted COBOL command must build and use the live schema."""
    dynamic = subprocess.run(
        ["readelf", "-d", "/app/wire/bin/wire-terminal"],
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
    missing = run_cli("APPROVE", "REQ-U01", "WR-U01")
    signed = run_cli(
        "INITIATE",
        "REQ-U02",
        "WR-U01",
        "ACC-D1",
        "ACC-C1",
        "+500",
        "OP-A1",
    )
    assert missing.returncode == 2
    assert missing.stdout == ""
    assert "code=USAGE" in missing.stderr
    assert signed.returncode == 2
    assert scalar("SELECT count(*) FROM request_record") == 0


def test_initiate_approve_release_follow_public_state_machine() -> None:
    """A normal wire must advance once per accepted lifecycle command."""
    initiated = run_cli(
        "INITIATE", "REQ-L01", "WR-L01", "ACC-D1", "ACC-C1", "10000", "OP-A1"
    )
    approved = run_cli("APPROVE", "REQ-L02", "WR-L01", "1", "OP-A2")
    released = run_cli("RELEASE", "REQ-L03", "WR-L01", "2")
    status = run_cli("STATUS", "WR-L01")

    assert initiated.stdout.endswith(
        "|revision=000001|state=INITIATED|"
        "debit=000001000000|credit=000000100000|audit=0000000001\n"
    )
    assert "|revision=000002|state=APPROVED|" in approved.stdout
    assert "|revision=000003|state=RELEASED|" in released.stdout
    assert "|debit=000000990000|credit=000000110000|" in released.stdout
    assert "|state=RELEASED|" in status.stdout
    assert str(scalar("SELECT state FROM wire_request")).strip() == "RELEASED"


def test_cancel_handles_initiated_and_approved_wires() -> None:
    """Cancellation must work in both allowed pre-release states."""
    assert (
        run_cli(
            "INITIATE",
            "REQ-C01",
            "WR-C01",
            "ACC-D1",
            "ACC-C1",
            "1000",
            "OP-A1",
        ).returncode
        == 0
    )
    cancelled_open = run_cli("CANCEL", "REQ-C02", "WR-C01", "1")
    assert "|revision=000002|state=CANCELLED|" in cancelled_open.stdout

    assert (
        run_cli(
            "INITIATE",
            "REQ-C03",
            "WR-C02",
            "ACC-D1",
            "ACC-C1",
            "1000",
            "OP-A1",
        ).returncode
        == 0
    )
    assert run_cli("APPROVE", "REQ-C04", "WR-C02", "1", "OP-A2").returncode == 0
    cancelled_approved = run_cli("CANCEL", "REQ-C05", "WR-C02", "2")
    assert "|revision=000003|state=CANCELLED|" in cancelled_approved.stdout
    assert scalar("SELECT count(*) FROM ledger_entry") == 0


def test_rejection_precedence_is_stable_and_recorded() -> None:
    """Unknown wire must win over later revision and operator checks."""
    result = run_cli("APPROVE", "REQ-P01", "WR-NOPE", "999", "OP-Z9")
    assert result.returncode == 1
    assert result.stdout == (
        "ERR|request=REQ-P01|command=APPROVE|code=UNKNOWN_WIRE\n"
    )
    assert scalar("SELECT count(*) FROM request_record") == 1
    assert scalar("SELECT count(*) FROM audit_event") == 0
