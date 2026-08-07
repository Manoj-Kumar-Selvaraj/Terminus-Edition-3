"""Concurrent request identity and audit ordering checks."""

from concurrent.futures import ThreadPoolExecutor

from conftest import connection, run_cli, scalar


def test_simultaneous_identical_request_converges_on_one_result() -> None:
    """Two identical first uses must return one stored result, not an SQL error."""

    def submit() -> tuple[int, str, str]:
        result = run_cli(
            "INITIATE",
            "REQ-SAME",
            "WR-SAME",
            "ACC-D1",
            "ACC-C1",
            "5000",
            "OP-A1",
        )
        return result.returncode, result.stdout, result.stderr

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: submit(), range(2)))
    assert outcomes[0][0] == outcomes[1][0] == 0
    assert outcomes[0][1] == outcomes[1][1]
    assert outcomes[0][2] == outcomes[1][2] == ""
    assert scalar("SELECT count(*) FROM request_record") == 1
    assert scalar("SELECT count(*) FROM audit_event") == 1


def test_concurrent_accepts_publish_unique_gap_free_audit_numbers() -> None:
    """Concurrent unrelated initiates must serialize only their committed audit IDs."""
    commands = [
        (
            "INITIATE",
            f"REQ-Q{index:02d}",
            f"WR-Q{index:02d}",
            "ACC-D1",
            "ACC-C1",
            "1000",
            "OP-A1",
        )
        for index in range(1, 5)
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda command: run_cli(*command), commands))
    assert all(result.returncode == 0 for result in results)
    with connection() as conn:
        sequences = [
            row[0]
            for row in conn.execute(
                "SELECT audit_sequence FROM audit_event ORDER BY audit_sequence"
            )
        ]
    assert sequences == list(range(1, 5))
    assert len({result.stdout for result in results}) == 4


def test_unrelated_wires_both_commit_under_concurrency() -> None:
    """Independent wires must not block each other from committing."""
    commands = [
        (
            "INITIATE",
            "REQ-U11",
            "WR-U11",
            "ACC-D1",
            "ACC-C1",
            "1000",
            "OP-A1",
        ),
        (
            "INITIATE",
            "REQ-U12",
            "WR-U12",
            "ACC-D2",
            "ACC-C2",
            "2000",
            "OP-B1",
        ),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda command: run_cli(*command), commands))
    assert all(result.returncode == 0 for result in results)
    assert scalar("SELECT count(*) FROM wire_request") == 2
