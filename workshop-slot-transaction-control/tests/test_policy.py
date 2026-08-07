"""Compiled roster policy and persisted decision checks."""

from conftest import connection, run_cli, scalar


def test_alternating_rosters_shift_the_medium_priority_start_window() -> None:
    """The same priority/hour must differ across the documented A and B rosters."""
    assert run_cli("OPEN", "REQ-P11", "WO-P11", "TRANSPORT", "4").returncode == 0
    roster_a = run_cli(
        "RESERVE", "REQ-P12", "WO-P11", "1", "BAY-T1", "TECH-T1", "240", "300"
    )
    assert roster_a.returncode == 0

    assert run_cli("OPEN", "REQ-P13", "WO-P12", "TRANSPORT", "4").returncode == 0
    roster_b = run_cli(
        "RESERVE", "REQ-P14", "WO-P12", "1", "BAY-T2", "TECH-T2", "10320", "10380"
    )
    assert roster_b.returncode == 1
    assert "code=INVALID_WINDOW" in roster_b.stdout


def test_class_and_priority_duration_limit_accepts_boundary_only() -> None:
    """A radio priority-three slot may equal its limit but may not exceed it."""
    assert run_cli("OPEN", "REQ-D01", "WO-D01", "RADIO", "3").returncode == 0
    boundary = run_cli(
        "RESERVE", "REQ-D02", "WO-D01", "1", "BAY-R1", "TECH-R1", "0", "420"
    )
    assert boundary.returncode == 0

    assert run_cli("OPEN", "REQ-D03", "WO-D02", "RADIO", "3").returncode == 0
    too_long = run_cli(
        "RESERVE", "REQ-D04", "WO-D02", "1", "BAY-R1", "TECH-R1", "1000", "1421"
    )
    assert too_long.returncode == 1
    assert "code=INVALID_WINDOW" in too_long.stdout
    assert scalar("SELECT count(*) FROM booking") == 1


def test_policy_decision_fields_are_stored_with_each_booking() -> None:
    """Roster, shift, supervision, and capacity must come from one decision."""
    assert run_cli("OPEN", "REQ-F01", "WO-F01", "TRANSPORT", "1").returncode == 0
    assert run_cli(
        "RESERVE", "REQ-F02", "WO-F01", "1", "BAY-T1", "TECH-T1", "60", "120"
    ).returncode == 0
    assert run_cli("OPEN", "REQ-F03", "WO-F02", "TRANSPORT", "7").returncode == 0
    assert run_cli(
        "RESERVE", "REQ-F04", "WO-F02", "1", "BAY-T2", "TECH-T2", "10500", "10560"
    ).returncode == 0

    with connection() as conn:
        rows = [
            (str(row[0]).strip(), str(row[1]).strip(), row[2], row[3])
            for row in conn.execute(
                "SELECT policy_id, shift_code, supervision_level, capacity_percent "
                "FROM booking ORDER BY work_order_id"
            )
        ]
    assert rows == [
        ("TR-01-01-A", "N", 3, 100),
        ("TR-07-07-B", "D", 1, 70),
    ]


def test_move_replaces_policy_decision_only_after_full_approval() -> None:
    """A valid move updates its policy fields while a later invalid move changes none."""
    assert run_cli("OPEN", "REQ-V01", "WO-V01", "TRANSPORT", "2").returncode == 0
    assert run_cli(
        "RESERVE", "REQ-V02", "WO-V01", "1", "BAY-T1", "TECH-T1", "60", "120"
    ).returncode == 0
    moved = run_cli(
        "MOVE", "REQ-V03", "WO-V01", "2", "BAY-T2", "TECH-T2", "10560", "10660"
    )
    assert moved.returncode == 0
    with connection() as conn:
        approved = conn.execute(
            "SELECT bay_id, start_tick, end_tick, policy_id, revision FROM booking"
        ).fetchone()
    assert approved is not None
    assert str(approved[0]).strip() == "BAY-T2"
    assert str(approved[3]).strip() == "TR-02-08-B"
    assert approved[4] == 2

    rejected = run_cli(
        "MOVE", "REQ-V04", "WO-V01", "3", "BAY-T1", "TECH-T1", "20000", "20751"
    )
    with connection() as conn:
        after = conn.execute(
            "SELECT bay_id, start_tick, end_tick, policy_id, revision FROM booking"
        ).fetchone()
    assert rejected.returncode == 1
    assert "code=INVALID_WINDOW" in rejected.stdout
    assert after == approved
