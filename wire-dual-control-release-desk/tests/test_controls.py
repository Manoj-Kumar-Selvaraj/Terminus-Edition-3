"""Dual-control, freeze, and funds-gate control checks."""

from conftest import connection, run_cli, scalar


def prepare_approved(
    wire: str,
    debit: str = "ACC-D1",
    credit: str = "ACC-C1",
    amount: int = 10000,
) -> None:
    """Create an approved wire ready for RELEASE."""
    assert (
        run_cli(
            "INITIATE",
            f"REQ-{wire}-I",
            wire,
            debit,
            credit,
            amount,
            "OP-A1",
        ).returncode
        == 0
    )
    assert run_cli("APPROVE", f"REQ-{wire}-A", wire, "1", "OP-A2").returncode == 0


def test_approver_must_differ_from_initiator() -> None:
    """Dual-control rejects the same operator on APPROVE."""
    assert (
        run_cli(
            "INITIATE",
            "REQ-DC01",
            "WR-DC01",
            "ACC-D1",
            "ACC-C1",
            "5000",
            "OP-A1",
        ).returncode
        == 0
    )
    same = run_cli("APPROVE", "REQ-DC02", "WR-DC01", "1", "OP-A1")
    assert same.returncode == 1
    assert same.stdout == (
        "ERR|request=REQ-DC02|command=APPROVE|code=SAME_OPERATOR\n"
    )
    assert str(scalar("SELECT state FROM wire_request")).strip() == "INITIATED"
    assert scalar("SELECT approver_id FROM wire_request") is None


def test_frozen_account_rejects_release_without_balance_change() -> None:
    """Either frozen endpoint must fail RELEASE before posting."""
    prepare_approved("WR-FZ01", debit="ACC-FZ", credit="ACC-C1", amount=1000)
    frozen = run_cli("RELEASE", "REQ-FZ01", "WR-FZ01", "2")
    assert frozen.returncode == 1
    assert "code=ACCOUNT_FROZEN" in frozen.stdout
    assert scalar("SELECT count(*) FROM ledger_entry") == 0
    assert scalar(
        "SELECT balance_cents FROM wire_account WHERE account_id='ACC-FZ'"
    ) == 800000
    assert scalar(
        "SELECT balance_cents FROM wire_account WHERE account_id='ACC-C1'"
    ) == 100000


def test_insufficient_funds_rejects_release_without_ledger_rows() -> None:
    """Debit balances below the wire amount must fail closed."""
    prepare_approved("WR-IF01", debit="ACC-LOW", credit="ACC-C2", amount=500)
    short = run_cli("RELEASE", "REQ-IF01", "WR-IF01", "2")
    assert short.returncode == 1
    assert "code=INSUFFICIENT_FUNDS" in short.stdout
    assert scalar("SELECT count(*) FROM ledger_entry") == 0
    assert scalar(
        "SELECT balance_cents FROM wire_account WHERE account_id='ACC-LOW'"
    ) == 250


def test_credit_side_frozen_also_blocks_release() -> None:
    """A frozen credit account is rejected with ACCOUNT_FROZEN as well."""
    prepare_approved("WR-FZ02", debit="ACC-D2", credit="ACC-FZ", amount=1000)
    frozen = run_cli("RELEASE", "REQ-FZ02", "WR-FZ02", "2")
    assert frozen.returncode == 1
    assert "code=ACCOUNT_FROZEN" in frozen.stdout
    with connection() as conn:
        debit_balance = conn.execute(
            "SELECT balance_cents FROM wire_account WHERE account_id='ACC-D2'"
        ).fetchone()[0]
    assert debit_balance == 500000
