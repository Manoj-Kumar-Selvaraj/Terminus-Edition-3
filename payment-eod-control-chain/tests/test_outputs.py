import csv
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

ROOT = Path("/app/eod")
DB = ROOT / "state" / "payment_eod.db"
OUT = ROOT / "out"
SCHEMA = ROOT / "sql" / "schema.sql"
RUNNER = ROOT / "bin" / "run_eod.sh"

BASE_SEED = """
INSERT INTO cycles(cycle_id,business_date,source,run_id) VALUES
('CYCLE-T1','2026-08-07','CORP-ACH','RUN-T1');
INSERT INTO accounts(account_id,status,balance_cents) VALUES
('A100','ACTIVE',250000),('A200','ACTIVE',50000),('A300','ACTIVE',300000),('A400','ACTIVE',90000);
INSERT INTO payment_history(source_ref,payer_account,beneficiary_ref,amount_cents,currency,purpose,status) VALUES
('SRC-REPLAY-1','A300','A400',12000,'INR','TRANSFER','COMPLETED'),
('SRC-OLD-EXT','A300','B-EXT-1',25000,'INR','VENDOR','ACCEPTED');
INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose) VALUES
(1,'CYCLE-T1','SRC-INT-1','A100','A200','A200',30000,100,50,'INR','TRANSFER'),
(2,'CYCLE-T1','SRC-EXT-1','A300','B-EXT-1',NULL,25000,200,100,'INR','VENDOR'),
(3,'CYCLE-T1','SRC-REPLAY-1','A300','A400','A400',12000,0,0,'INR','TRANSFER'),
(4,'CYCLE-T1','SRC-EXT-2','A300','B-EXT-1',NULL,25000,200,100,'INR','VENDOR');
INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete)
VALUES ('CYCLE-T1',1,1,1);
"""


def reset_db(seed_sql: str) -> None:
    """Recreate authoritative SQL state and remove artifacts for an independent scenario."""
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA.read_text())
    con.executescript(seed_sql)
    con.commit()
    con.close()


def run_batch() -> subprocess.CompletedProcess[str]:
    """Execute the submitted shell batch controller and capture diagnostic output."""
    return subprocess.run(
        ["bash", str(RUNNER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=True,
    )


def rows(sql: str):
    """Return query rows from the authoritative database."""
    con = sqlite3.connect(DB)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def read_csv(path: Path):
    """Read one published CSV artifact as dictionaries."""
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def csv_header(path: Path):
    """Return the declared CSV header fields in order."""
    with path.open(newline="") as f:
        return next(csv.reader(f))


def reconciliation():
    """Load the required reconciliation artifact."""
    return json.loads((OUT / "reconciliation.json").read_text())


def test_balanced_cycle_preserves_population_and_financial_semantics():
    """A clean cycle must classify replay correctly, preserve one financial effect per success, and reconcile."""
    reset_db(BASE_SEED)
    run_batch()

    assert csv_header(OUT / "customer_response.csv") == ["payment_id", "source_ref", "outcome", "reason"]
    assert csv_header(OUT / "clearing_submission.csv") == ["payment_id", "source_ref", "amount_cents", "currency"]

    response = {int(r["payment_id"]): r for r in read_csv(OUT / "customer_response.csv")}
    assert set(response) == {1, 2, 3, 4}
    assert response[1]["outcome"] == "SUCCESS_INTERNAL"
    assert response[2]["outcome"] == "SUCCESS_EXTERNAL"
    assert response[3]["outcome"] == "DUPLICATE"
    assert response[4]["outcome"] == "SUCCESS_EXTERNAL"

    rec = reconciliation()
    assert rec == {
        "cycle_id": "CYCLE-T1",
        "status": "BALANCED",
        "original_count": 4,
        "final_count": 4,
        "original_value_cents": 92000,
        "response_value_cents": 92000,
        "internal_success_count": 1,
        "internal_posting_count": 1,
        "external_success_count": 2,
        "reservation_count": 2,
        "clearing_count": 2,
        "reserved_debit_cents": 50600,
        "clearing_value_cents": 50000,
        "external_fee_tax_cents": 600,
        "ledger_debits_cents": 80750,
        "ledger_credits_cents": 80750,
        "difference_count": 0,
    }

    assert rows("SELECT balance_cents FROM accounts WHERE account_id='A100'") == [(219850,)]
    assert rows("SELECT balance_cents FROM accounts WHERE account_id='A200'") == [(80000,)]
    assert {int(r["payment_id"]) for r in read_csv(OUT / "clearing_submission.csv")} == {2, 4}

    ledger = set(rows("SELECT payment_id,side,account_code,amount_cents FROM ledger_entries"))
    assert ledger == {
        (1, "D", "CUSTOMER_CONTROL", 30150),
        (1, "C", "BENEFICIARY_CONTROL", 30000),
        (1, "C", "FEE_INCOME", 100),
        (1, "C", "TAX_PAYABLE", 50),
        (2, "D", "CUSTOMER_RESERVED", 25300),
        (2, "C", "CLEARING_PAYABLE", 25000),
        (2, "C", "FEE_INCOME", 200),
        (2, "C", "TAX_PAYABLE", 100),
        (4, "D", "CUSTOMER_RESERVED", 25300),
        (4, "C", "CLEARING_PAYABLE", 25000),
        (4, "C", "FEE_INCOME", 200),
        (4, "C", "TAX_PAYABLE", 100),
    }
    assert rows(
        "SELECT (SELECT COUNT(*) FROM internal_postings WHERE payment_id=3),"
        "(SELECT COUNT(*) FROM reservations WHERE payment_id=3 AND active=1),"
        "(SELECT COUNT(*) FROM clearing_items WHERE payment_id=3),"
        "(SELECT COUNT(*) FROM ledger_entries WHERE payment_id=3)"
    ) == [(0, 0, 0, 0)]

    assert json.loads((OUT / "success_authorization.json").read_text()) == {
        "cycle_id": "CYCLE-T1",
        "business_date": "2026-08-07",
        "source": "CORP-ACH",
        "run_id": "RUN-T1",
        "status": "AUTHORIZED",
    }
    assert rows("SELECT completion_status FROM cycles") == [("COMPLETED",)]


def test_rerunning_a_completed_cycle_does_not_repeat_financial_effects():
    """Running the same completed cycle twice must preserve one posting, reservation, clearing, ledger, and authorization effect."""
    reset_db(BASE_SEED)
    run_batch()
    first = {
        "balances": rows("SELECT account_id,balance_cents FROM accounts ORDER BY account_id"),
        "postings": rows("SELECT payment_id,debit_cents,beneficiary_credit_cents FROM internal_postings ORDER BY payment_id"),
        "reservations": rows("SELECT payment_id,amount_cents,active FROM reservations ORDER BY payment_id"),
        "clearing": rows("SELECT payment_id,amount_cents,currency FROM clearing_items ORDER BY payment_id"),
        "ledger": rows("SELECT payment_id,side,account_code,amount_cents FROM ledger_entries ORDER BY payment_id,side,account_code"),
    }
    run_batch()
    second = {
        "balances": rows("SELECT account_id,balance_cents FROM accounts ORDER BY account_id"),
        "postings": rows("SELECT payment_id,debit_cents,beneficiary_credit_cents FROM internal_postings ORDER BY payment_id"),
        "reservations": rows("SELECT payment_id,amount_cents,active FROM reservations ORDER BY payment_id"),
        "clearing": rows("SELECT payment_id,amount_cents,currency FROM clearing_items ORDER BY payment_id"),
        "ledger": rows("SELECT payment_id,side,account_code,amount_cents FROM ledger_entries ORDER BY payment_id,side,account_code"),
    }
    assert second == first
    assert rows("SELECT COUNT(*) FROM success_authorizations") == [(1,)]
    assert reconciliation()["status"] == "BALANCED"


def test_resume_uses_existing_external_reservation_instead_of_creating_another():
    """A partial external state must be resumed once and its active reservation must still reduce later payer capacity."""
    seed = """
    INSERT INTO cycles(cycle_id,business_date,source,run_id) VALUES('CYCLE-T2','2026-08-08','CORP-ACH','RUN-T2');
    INSERT INTO accounts(account_id,status,balance_cents) VALUES('A500','ACTIVE',50000);
    INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose) VALUES
    (20,'CYCLE-T2','SRC-20','A500','B20',NULL,30000,200,100,'INR','VENDOR'),
    (21,'CYCLE-T2','SRC-21','A500','B21',NULL,25000,200,100,'INR','VENDOR');
    INSERT INTO reservations(payment_id,amount_cents,active) VALUES(20,30300,1);
    INSERT INTO ledger_entries(payment_id,side,account_code,amount_cents) VALUES
    (20,'D','CUSTOMER_RESERVED',30300),(20,'C','CLEARING_PAYABLE',30000),(20,'C','FEE_INCOME',200),(20,'C','TAX_PAYABLE',100);
    INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete) VALUES('CYCLE-T2',1,1,1);
    """
    reset_db(seed)
    run_batch()

    assert rows("SELECT payment_id,COUNT(*) FROM reservations WHERE active=1 GROUP BY payment_id ORDER BY payment_id") == [(20, 1)]
    assert rows("SELECT payment_id,outcome FROM payment_outcomes ORDER BY payment_id") == [
        (20, "SUCCESS_EXTERNAL"),
        (21, "REJECTED"),
    ]
    assert rows("SELECT payment_id FROM clearing_items ORDER BY payment_id") == [(20,)]
    assert reconciliation()["status"] == "BALANCED"


def test_resume_uses_existing_internal_posting_without_reapplying_balances_or_ledger():
    """A partially completed internal payment must retain its existing posting and ledger as the authoritative effect."""
    seed = """
    INSERT INTO cycles(cycle_id,business_date,source,run_id) VALUES('CYCLE-T3','2026-08-09','CORP-ACH','RUN-T3');
    INSERT INTO accounts(account_id,status,balance_cents) VALUES('A600','ACTIVE',79850),('A601','ACTIVE',25000);
    INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose)
    VALUES(30,'CYCLE-T3','SRC-30','A600','A601','A601',20000,100,50,'INR','TRANSFER');
    INSERT INTO internal_postings(payment_id,debit_cents,beneficiary_credit_cents) VALUES(30,20150,20000);
    INSERT INTO ledger_entries(payment_id,side,account_code,amount_cents) VALUES
    (30,'D','CUSTOMER_CONTROL',20150),(30,'C','BENEFICIARY_CONTROL',20000),(30,'C','FEE_INCOME',100),(30,'C','TAX_PAYABLE',50);
    INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete) VALUES('CYCLE-T3',1,1,1);
    """
    reset_db(seed)
    before_balances = rows("SELECT account_id,balance_cents FROM accounts ORDER BY account_id")
    before_ledger = rows("SELECT payment_id,side,account_code,amount_cents FROM ledger_entries ORDER BY entry_id")
    run_batch()

    assert rows("SELECT account_id,balance_cents FROM accounts ORDER BY account_id") == before_balances
    assert rows("SELECT COUNT(*) FROM internal_postings WHERE payment_id=30") == [(1,)]
    assert rows("SELECT payment_id,side,account_code,amount_cents FROM ledger_entries ORDER BY entry_id") == before_ledger
    assert rows("SELECT outcome FROM payment_outcomes WHERE payment_id=30") == [("SUCCESS_INTERNAL",)]
    assert reconciliation()["status"] == "BALANCED"


def test_ineligible_internal_beneficiary_has_no_partial_financial_result():
    """An internal payment rejected at execution time must leave balances, postings, and ledger state untouched."""
    seed = """
    INSERT INTO cycles(cycle_id,business_date,source,run_id) VALUES('CYCLE-T4','2026-08-10','CORP-ACH','RUN-T4');
    INSERT INTO accounts(account_id,status,balance_cents) VALUES('A700','ACTIVE',100000),('A701','BLOCKED',5000);
    INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose)
    VALUES(40,'CYCLE-T4','SRC-40','A700','A701','A701',20000,100,50,'INR','TRANSFER');
    INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete) VALUES('CYCLE-T4',1,1,1);
    """
    reset_db(seed)
    run_batch()

    assert rows("SELECT account_id,balance_cents FROM accounts ORDER BY account_id") == [("A700", 100000), ("A701", 5000)]
    assert rows("SELECT COUNT(*) FROM internal_postings") == [(0,)]
    assert rows("SELECT COUNT(*) FROM ledger_entries") == [(0,)]
    assert rows("SELECT outcome FROM payment_outcomes WHERE payment_id=40") == [("REJECTED",)]
    assert reconciliation()["status"] == "BALANCED"


def test_unbalanced_existing_external_effect_blocks_publication_and_removes_stale_artifacts():
    """A mismatched reservation must hold reconciliation and a held rerun must leave no official stale publication or authorization."""
    seed = """
    INSERT INTO cycles(cycle_id,business_date,source,run_id) VALUES('CYCLE-T5','2026-08-11','CORP-ACH','RUN-T5');
    INSERT INTO accounts(account_id,status,balance_cents) VALUES('A800','ACTIVE',100000);
    INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose)
    VALUES(50,'CYCLE-T5','SRC-50','A800','B50',NULL,10000,100,0,'INR','VENDOR');
    INSERT INTO reservations(payment_id,amount_cents,active) VALUES(50,9999,1);
    INSERT INTO ledger_entries(payment_id,side,account_code,amount_cents) VALUES
    (50,'D','CUSTOMER_RESERVED',9999),(50,'C','CLEARING_PAYABLE',9899),(50,'C','FEE_INCOME',100);
    INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete) VALUES('CYCLE-T5',1,1,1);
    """
    reset_db(seed)
    (OUT / "customer_response.csv").write_text("stale\n")
    (OUT / "clearing_submission.csv").write_text("stale\n")
    (OUT / "success_authorization.json").write_text("{}\n")
    run_batch()

    rec = reconciliation()
    assert rec["status"] == "HELD"
    assert rec["difference_count"] > 0
    assert not (OUT / "customer_response.csv").exists()
    assert not (OUT / "clearing_submission.csv").exists()
    assert not (OUT / "success_authorization.json").exists()
    assert rows("SELECT completion_status FROM cycles") == [("HELD",)]
    assert rows("SELECT COUNT(*) FROM success_authorizations") == [(0,)]


@pytest.mark.parametrize(
    "delivery_ack,report_complete,archive_complete",
    [(0, 1, 1), (1, 0, 1), (1, 1, 0)],
    ids=["delivery", "report", "archive"],
)
def test_each_close_prerequisite_can_hold_authorization(delivery_ack: int, report_complete: int, archive_complete: int):
    """Balanced finance may publish responses, but any missing close prerequisite must keep completion held and unauthorized."""
    seed = BASE_SEED.replace("('CYCLE-T1',1,1,1)", f"('CYCLE-T1',{delivery_ack},{report_complete},{archive_complete})")
    reset_db(seed)
    run_batch()

    assert reconciliation()["status"] == "BALANCED"
    assert (OUT / "customer_response.csv").exists()
    assert (OUT / "clearing_submission.csv").exists()
    assert rows("SELECT completion_status FROM cycles") == [("HELD",)]
    assert rows("SELECT status FROM completion_register") == [("HELD",)]
    assert rows("SELECT COUNT(*) FROM success_authorizations") == [(0,)]
    assert not (OUT / "success_authorization.json").exists()


def test_pending_history_is_not_an_accepted_replay():
    """A pending history row with the same source reference must not be treated as an already accepted duplicate."""
    seed = """
    INSERT INTO cycles(cycle_id,business_date,source,run_id) VALUES('CYCLE-T6','2026-08-12','CORP-ACH','RUN-T6');
    INSERT INTO accounts(account_id,status,balance_cents) VALUES('A900','ACTIVE',100000);
    INSERT INTO payment_history(source_ref,payer_account,beneficiary_ref,amount_cents,currency,purpose,status)
    VALUES('SRC-PENDING','A900','B90',15000,'INR','VENDOR','PENDING');
    INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose)
    VALUES(60,'CYCLE-T6','SRC-PENDING','A900','B90',NULL,15000,100,50,'INR','VENDOR');
    INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete) VALUES('CYCLE-T6',1,1,1);
    """
    reset_db(seed)
    run_batch()

    assert rows("SELECT outcome FROM payment_outcomes WHERE payment_id=60") == [("SUCCESS_EXTERNAL",)]
    assert rows("SELECT COUNT(*) FROM reservations WHERE payment_id=60 AND active=1") == [(1,)]
    assert rows("SELECT COUNT(*) FROM clearing_items WHERE payment_id=60") == [(1,)]
    assert reconciliation()["status"] == "BALANCED"


def test_cobol_duplicate_interface_uses_accepted_source_reference_not_commercial_similarity():
    """The submitted PAYDUP interface must separate an exact accepted replay from a commercially similar new instruction."""
    work = ROOT / "work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "history.psv").write_text("OLD-1|A1|BEN-X|10000|INR|VENDOR|ACCEPTED\n")
    (work / "dup_input.psv").write_text(
        "1|OLD-1|A1|BEN-X|10000|INR|VENDOR\n"
        "2|NEW-2|A1|BEN-X|10000|INR|VENDOR\n"
    )
    binary = Path("/tmp/paydup_direct")
    subprocess.run(
        ["cobc", "-x", "-free", "-o", str(binary), str(ROOT / "cobol" / "paydup.cob")],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run([str(binary)], check=True, capture_output=True, text=True)
    result = {}
    for line in (work / "dup_output.psv").read_text().splitlines():
        parts = [part.strip() for part in line.split("|")]
        result[int(parts[0])] = parts[1]
    assert result == {1: "DUPLICATE", 2: "UNIQUE"}


def test_cobol_execution_interface_handles_resume_eligibility_and_capacity():
    """The submitted PAYEXEC interface must distinguish resumed effects, eligibility rejection, capacity rejection, and new execution."""
    work = ROOT / "work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "exec_input.psv").write_text(
        "10|I|ACTIVE|ACTIVE|50000|10000|100|50|NONE\n"
        "11|E|ACTIVE|NA|50000|20000|200|100|EXTERNAL\n"
        "12|I|ACTIVE|BLOCKED|50000|10000|0|0|NONE\n"
        "13|E|ACTIVE|NA|9000|10000|0|0|NONE\n"
        "14|E|BLOCKED|NA|50000|10000|0|0|NONE\n"
    )
    binary = Path("/tmp/payexec_direct")
    subprocess.run(
        ["cobc", "-x", "-free", "-o", str(binary), str(ROOT / "cobol" / "payexec.cob")],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run([str(binary)], check=True, capture_output=True, text=True)
    actions = {}
    for line in (work / "exec_output.psv").read_text().splitlines():
        parts = [part.strip() for part in line.split("|")]
        actions[int(parts[0])] = parts[1]
    assert actions == {
        10: "POST_INTERNAL",
        11: "ALREADY_EXTERNAL",
        12: "REJECT",
        13: "REJECT",
        14: "REJECT",
    }
