import csv
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

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


def reconciliation():
    """Load the required reconciliation artifact."""
    return json.loads((OUT / "reconciliation.json").read_text())


def test_balanced_cycle_preserves_population_and_distinguishes_replay_from_recurrence():
    """A clean cycle must classify exact replay only, retain recurring activity, and reconcile all payments."""
    reset_db(BASE_SEED)
    run_batch()

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
    clearing = read_csv(OUT / "clearing_submission.csv")
    assert {int(r["payment_id"]) for r in clearing} == {2, 4}
    assert (OUT / "success_authorization.json").exists()


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


def test_resume_uses_existing_reservation_and_capacity_without_creating_a_second_one():
    """A partial external state must be resumed once and must still reduce capacity available to later payments."""
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


def test_ineligible_internal_beneficiary_has_no_partial_financial_result():
    """An internal payment rejected at execution time must leave balances, postings, and ledger state untouched."""
    seed = """
    INSERT INTO cycles(cycle_id,business_date,source,run_id) VALUES('CYCLE-T3','2026-08-09','CORP-ACH','RUN-T3');
    INSERT INTO accounts(account_id,status,balance_cents) VALUES('A600','ACTIVE',100000),('A601','BLOCKED',5000);
    INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose)
    VALUES(30,'CYCLE-T3','SRC-30','A600','A601','A601',20000,100,50,'INR','TRANSFER');
    INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete) VALUES('CYCLE-T3',1,1,1);
    """
    reset_db(seed)
    run_batch()

    assert rows("SELECT account_id,balance_cents FROM accounts ORDER BY account_id") == [("A600", 100000), ("A601", 5000)]
    assert rows("SELECT COUNT(*) FROM internal_postings") == [(0,)]
    assert rows("SELECT COUNT(*) FROM ledger_entries") == [(0,)]
    assert rows("SELECT outcome FROM payment_outcomes WHERE payment_id=30") == [("REJECTED",)]
    assert reconciliation()["status"] == "BALANCED"


def test_unbalanced_existing_external_effect_blocks_publication_and_success():
    """A reservation/clearing value difference must hold reconciliation and suppress official outbound artifacts."""
    seed = """
    INSERT INTO cycles(cycle_id,business_date,source,run_id) VALUES('CYCLE-T4','2026-08-10','CORP-ACH','RUN-T4');
    INSERT INTO accounts(account_id,status,balance_cents) VALUES('A700','ACTIVE',100000);
    INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,amount_cents,fee_cents,tax_cents,currency,purpose)
    VALUES(40,'CYCLE-T4','SRC-40','A700','B40',NULL,10000,100,0,'INR','VENDOR');
    INSERT INTO reservations(payment_id,amount_cents,active) VALUES(40,9999,1);
    INSERT INTO ledger_entries(payment_id,side,account_code,amount_cents) VALUES
    (40,'D','CUSTOMER_RESERVED',9999),(40,'C','CLEARING_PAYABLE',9899),(40,'C','FEE_INCOME',100);
    INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete) VALUES('CYCLE-T4',1,1,1);
    """
    reset_db(seed)
    run_batch()

    rec = reconciliation()
    assert rec["status"] == "HELD"
    assert rec["difference_count"] > 0
    assert not (OUT / "customer_response.csv").exists()
    assert not (OUT / "clearing_submission.csv").exists()
    assert not (OUT / "success_authorization.json").exists()
    assert rows("SELECT completion_status FROM cycles") == [("HELD",)]
    assert rows("SELECT COUNT(*) FROM success_authorizations") == [(0,)]


def test_completion_prerequisite_can_hold_success_after_financial_reconciliation():
    """Balanced finance may publish responses, but missing delivery acknowledgement must keep completion held and success unauthorized."""
    reset_db(BASE_SEED.replace("('CYCLE-T1',1,1,1)", "('CYCLE-T1',0,1,1)"))
    run_batch()

    assert reconciliation()["status"] == "BALANCED"
    assert (OUT / "customer_response.csv").exists()
    assert (OUT / "clearing_submission.csv").exists()
    assert rows("SELECT completion_status FROM cycles") == [("HELD",)]
    assert rows("SELECT status FROM completion_register") == [("HELD",)]
    assert rows("SELECT COUNT(*) FROM success_authorizations") == [(0,)]
    assert not (OUT / "success_authorization.json").exists()


def test_cobol_duplicate_interface_uses_accepted_source_reference_not_commercial_similarity():
    """The submitted PAYDUP COBOL interface must separate exact accepted replay from a similar new instruction."""
    work = ROOT / "work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "history.psv").write_text(
        "OLD-1|A1|BEN-X|10000|INR|VENDOR|ACCEPTED\n"
    )
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
    """The submitted PAYEXEC COBOL interface must distinguish resume, rejection, and authorized execution actions."""
    work = ROOT / "work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "exec_input.psv").write_text(
        "10|I|ACTIVE|ACTIVE|50000|10000|100|50|NONE\n"
        "11|E|ACTIVE|NA|50000|20000|200|100|EXTERNAL\n"
        "12|I|ACTIVE|BLOCKED|50000|10000|0|0|NONE\n"
        "13|E|ACTIVE|NA|9000|10000|0|0|NONE\n"
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
    }
