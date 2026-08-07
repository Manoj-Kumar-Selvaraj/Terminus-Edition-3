"""Concurrent request, resource-lock, and audit ordering checks."""

from concurrent.futures import ThreadPoolExecutor

from conftest import connection, run_cli, scalar


def create_order(index: int) -> None:
    """Create a transport order used by a later concurrent claim."""
    result = run_cli(
        "OPEN", f"REQ-O{index:02d}", f"WO-O{index:02d}", "TRANSPORT", "2"
    )
    assert result.returncode == 0


def test_simultaneous_identical_request_converges_on_one_result() -> None:
    """Two identical first uses must return one stored result, not an SQL error."""
    def submit() -> tuple[int, str, str]:
        result = run_cli("OPEN", "REQ-SAME", "WO-SAME", "TRANSPORT", "2")
        return result.returncode, result.stdout, result.stderr

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: submit(), range(2)))
    assert outcomes[0][0] == outcomes[1][0] == 0
    assert outcomes[0][1] == outcomes[1][1]
    assert outcomes[0][2] == outcomes[1][2] == ""
    assert scalar("SELECT count(*) FROM request_record") == 1
    assert scalar("SELECT count(*) FROM audit_event") == 1


def test_competing_bay_claims_have_one_committed_winner() -> None:
    """Overlapping claims on one bay must leave exactly one active booking."""
    create_order(1)
    create_order(2)

    commands = [
        ("RESERVE", "REQ-B01", "WO-O01", "1", "BAY-T1", "TECH-T1", "100", "200"),
        ("RESERVE", "REQ-B02", "WO-O02", "1", "BAY-T1", "TECH-T2", "100", "200"),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda command: run_cli(*command), commands))
    assert sorted(result.returncode for result in results) == [0, 1]
    assert sum("code=RESOURCE_BUSY" in result.stdout for result in results) == 1
    assert scalar("SELECT count(*) FROM booking") == 1


def test_competing_technician_claims_lock_across_different_bays() -> None:
    """A technician must not be double-booked through independent bay locks."""
    create_order(3)
    create_order(4)
    commands = [
        ("RESERVE", "REQ-T01", "WO-O03", "1", "BAY-T1", "TECH-T1", "300", "400"),
        ("RESERVE", "REQ-T02", "WO-O04", "1", "BAY-T2", "TECH-T1", "300", "400"),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda command: run_cli(*command), commands))
    assert sorted(result.returncode for result in results) == [0, 1]
    assert sum("code=RESOURCE_BUSY" in result.stdout for result in results) == 1
    assert scalar("SELECT count(*) FROM booking") == 1


def test_unrelated_resource_claims_both_commit() -> None:
    """Locking one resource pair must not reject an independent reservation."""
    create_order(5)
    create_order(6)
    commands = [
        ("RESERVE", "REQ-U11", "WO-O05", "1", "BAY-T1", "TECH-T1", "500", "600"),
        ("RESERVE", "REQ-U12", "WO-O06", "1", "BAY-T2", "TECH-T2", "500", "600"),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda command: run_cli(*command), commands))
    assert all(result.returncode == 0 for result in results)
    assert scalar("SELECT count(*) FROM booking") == 2


def test_concurrent_accepts_publish_unique_gap_free_audit_numbers() -> None:
    """Concurrent unrelated opens must serialize only their committed audit IDs."""
    commands = [
        ("OPEN", f"REQ-Q{index:02d}", f"WO-Q{index:02d}", "GENERATOR", "2")
        for index in range(1, 5)
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda command: run_cli(*command), commands))
    assert all(result.returncode == 0 for result in results)
    with connection() as conn:
        sequences = [row[0] for row in conn.execute(
            "SELECT audit_sequence FROM audit_event ORDER BY audit_sequence"
        )]
    assert sequences == list(range(1, 5))
    assert len({result.stdout for result in results}) == 4
