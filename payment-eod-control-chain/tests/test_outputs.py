import csv
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

ROOT = Path('/app/eod')
DB = ROOT / 'state' / 'payment_eod.db'
OUT = ROOT / 'out'
SCHEMA = ROOT / 'sql' / 'schema.sql'
RUNNER = ROOT / 'bin' / 'run_eod.sh'
COBOL = ROOT / 'cobol'
VERIFY_BIN = Path('/tmp/eod-verifier-bin')


def reset_db(seed_sql: str) -> None:
    """Recreate authoritative state and output directories for one independent scenario."""
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.unlink(missing_ok=True)
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    try:
        con.execute('PRAGMA foreign_keys=ON')
        con.executescript(SCHEMA.read_text())
        con.executescript(seed_sql)
        con.commit()
    finally:
        con.close()


def run_batch() -> subprocess.CompletedProcess[str]:
    """Run the submitted EOD controller end to end."""
    return subprocess.run(
        ['bash', str(RUNNER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
        check=True,
    )


def rows(sql: str):
    """Return rows from the task database without mutating it."""
    con = sqlite3.connect(DB)
    try:
        con.execute('PRAGMA foreign_keys=ON')
        return con.execute(sql).fetchall()
    finally:
        con.close()


def scalar(sql: str):
    """Return the first scalar value from a query."""
    result = rows(sql)
    return result[0][0] if result else None


def read_csv(path: Path):
    """Read one CSV artifact into dictionaries."""
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def reconciliation():
    """Load the required reconciliation report."""
    return json.loads((OUT / 'reconciliation.json').read_text())


def compile_and_call(program: str, input_record: str) -> str:
    """Compile and invoke one documented COBOL decision interface."""
    VERIFY_BIN.mkdir(parents=True, exist_ok=True)
    binary = VERIFY_BIN / program
    subprocess.run(
        [
            'cobc',
            '-x',
            '-free',
            '-I',
            str(COBOL / 'copybooks'),
            '-o',
            str(binary),
            str(COBOL / f'{program}.cob'),
        ],
        check=True,
        text=True,
        capture_output=True,
        timeout=60,
    )
    completed = subprocess.run(
        [str(binary)],
        input=input_record + '\n',
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return completed.stdout.strip()


def cycle_sql(cycle='C1', date='2026-08-08', run='RUN-1', state='OPEN', recon='PENDING', close='PENDING'):
    """Build a cycle insert used by verifier scenarios."""
    return (
        "INSERT INTO cycles(cycle_id,business_date,source,run_id,state,reconciliation_status,completion_status) "
        f"VALUES('{cycle}','{date}','CORP-ACH','{run}','{state}','{recon}','{close}');\n"
    )


def prereq_sql(cycle='C1', delivery=1, report=1, archive=1):
    """Build close-prerequisite input for a cycle."""
    return (
        "INSERT INTO cycle_prerequisites(cycle_id,delivery_ack,report_complete,archive_complete) "
        f"VALUES('{cycle}',{delivery},{report},{archive});\n"
    )


def accounts_sql(*accounts):
    """Build account rows as (id,status,balance) tuples."""
    values = ','.join(f"('{a}','{status}',{balance},'INR')" for a, status, balance in accounts)
    return f"INSERT INTO accounts(account_id,status,balance_cents,currency) VALUES {values};\n"


def payment_sql(
    payment_id,
    source_ref,
    payer,
    beneficiary_ref,
    beneficiary_account,
    amount,
    fee=0,
    tax=0,
    cycle='C1',
    seq=10,
    purpose='TRANSFER',
):
    """Build one input payment row."""
    beneficiary_sql = 'NULL' if beneficiary_account is None else f"'{beneficiary_account}'"
    return (
        "INSERT INTO payments(payment_id,cycle_id,source_ref,payer_account,beneficiary_ref,beneficiary_account,"
        "amount_cents,fee_cents,tax_cents,currency,purpose,received_seq) VALUES("
        f"{payment_id},'{cycle}','{source_ref}','{payer}','{beneficiary_ref}',{beneficiary_sql},"
        f"{amount},{fee},{tax},'INR','{purpose}',{seq});\n"
    )


def history_sql(source_ref, payer, beneficiary_ref, amount, status='ACCEPTED', cycle=None, purpose='TRANSFER'):
    """Build one historical source-reference record."""
    cycle_sql_value = 'NULL' if cycle is None else f"'{cycle}'"
    return (
        "INSERT INTO payment_history(source_ref,accepted_cycle_id,payer_account,beneficiary_ref,amount_cents,currency,purpose,status) VALUES("
        f"'{source_ref}',{cycle_sql_value},'{payer}','{beneficiary_ref}',{amount},'INR','{purpose}','{status}');\n"
    )


def financial_snapshot():
    """Capture durable financial state while ignoring timestamps and diagnostic records."""
    return {
        'accounts': rows('SELECT account_id,balance_cents FROM accounts ORDER BY account_id'),
        'postings': rows('SELECT payment_id,cycle_id,payer_account,beneficiary_account,debit_cents,beneficiary_credit_cents FROM internal_postings ORDER BY posting_id'),
        'reservations': rows('SELECT payment_id,cycle_id,payer_account,amount_cents,active FROM reservations ORDER BY reservation_id'),
        'clearing': rows('SELECT payment_id,cycle_id,reservation_id,source_ref,amount_cents,currency,status FROM clearing_items ORDER BY clearing_id'),
        'ledger': rows('SELECT payment_id,cycle_id,side,account_code,amount_cents FROM ledger_entries ORDER BY entry_id'),
        'auth': rows('SELECT cycle_id,business_date,source,run_id,status FROM success_authorizations ORDER BY authorization_id'),
    }


# ---------------------------------------------------------------------------
# F2P: documented COBOL decision interfaces
# ---------------------------------------------------------------------------


def test_f2p_paydup_commercial_similarity_is_not_a_replay():
    """PAYDUP must use accepted source identity rather than commercial similarity as the replay key."""
    assert compile_and_call('paydup', 'N|Y|N|COMPLETED') == 'NEW'


def test_f2p_payelig_blocks_an_ineligible_internal_beneficiary():
    """PAYELIG must reject an internal transfer whose beneficiary account is blocked."""
    assert compile_and_call('payelig', 'ACTIVE|BLOCKED|INTERNAL') == 'REJECT_BENEFICIARY'


def test_f2p_paymoney_includes_fee_and_tax_in_total_debit():
    """PAYMONEY must calculate the full debit rather than principal alone."""
    assert int(compile_and_call('paymoney', '10000|200|100')) == 10300


def test_f2p_paycap_subtracts_other_active_reservations():
    """PAYCAP must compare the debit with balance after active reservations are removed."""
    assert compile_and_call('paycap', '50000|30000|25000') == 'INSUFFICIENT_CAPACITY'


def test_f2p_payroute_resumes_an_existing_internal_posting():
    """PAYROUTE must classify an existing internal posting as resumable work."""
    assert compile_and_call('payroute', 'INTERNAL|Y|N|N') == 'RESUME_INTERNAL'


def test_f2p_payroute_resumes_an_existing_external_reservation():
    """PAYROUTE must classify an existing external reservation as resumable work."""
    assert compile_and_call('payroute', 'EXTERNAL|N|Y|N') == 'RESUME_EXTERNAL'


def test_f2p_payrsv_rejects_a_mismatched_reservation_amount():
    """PAYRSV must hold a reservation whose durable debit differs from the expected debit."""
    assert compile_and_call('payrsv', '10300|10000|Y') == 'RESERVATION_MISMATCH'


def test_f2p_payclr_keeps_an_existing_clearing_item():
    """PAYCLR must retain a clearing item already linked to a matching reservation."""
    assert compile_and_call('payclr', 'Y|Y|Y') == 'KEEP_CLEARING'


def test_f2p_payledger_requires_the_complete_ledger_shape():
    """PAYLEDGER must reject equal debit/credit totals when required ledger rows are missing."""
    assert compile_and_call('payledger', '10300|10300|4|3') == 'LEDGER_INCOMPLETE'


def test_f2p_payrecon_checks_more_than_ledger_equality():
    """PAYRECON must hold a cycle with an invalid financial effect even when the ledger totals balance."""
    record = '1|1|10000|10000|0|0|0|0|0|0|0|0|0|0|1|0|0'
    assert compile_and_call('payrecon', record) == 'HELD'


def test_f2p_payclose_requires_report_and_archive_completion():
    """PAYCLOSE must not complete a balanced cycle when report/archive work is unfinished."""
    assert compile_and_call('payclose', 'BALANCED|1|0|1') == 'WAIT_CLOSE'


def test_f2p_paypub_holds_publication_when_reconciliation_is_held():
    """PAYPUB must gate official publication on BALANCED reconciliation."""
    assert compile_and_call('paypub', 'HELD') == 'HOLD'


def test_f2p_paystate_keeps_a_balanced_but_unclosed_cycle_reconciled():
    """PAYSTATE must not label balanced-but-waiting work as completed."""
    assert compile_and_call('paystate', 'PROCESSING|BALANCED|WAIT_CLOSE') == 'RECONCILED'


# ---------------------------------------------------------------------------
# F2P: end-to-end restart and control scenarios
# ---------------------------------------------------------------------------


def test_f2p_distinct_source_with_matching_commercial_details_executes_normally():
    """A new source reference remains new business even when prior commercial details are identical."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000), ('A2', 'ACTIVE', 1000))
        + history_sql('OLD-1', 'A1', 'A2', 10000, status='COMPLETED')
        + payment_sql(1, 'NEW-1', 'A1', 'A2', 'A2', 10000)
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert rows("SELECT outcome FROM payment_outcomes WHERE payment_id=1") == [('SUCCESS_INTERNAL',)]
    assert rows('SELECT COUNT(*) FROM internal_postings WHERE payment_id=1') == [(1,)]


def test_f2p_capacity_uses_principal_fee_and_tax():
    """A payer with capacity for principal but not total debit must be rejected without a partial effect."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 10000), ('A2', 'ACTIVE', 1000))
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 9900, fee=100, tax=50)
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert rows('SELECT outcome FROM payment_outcomes WHERE payment_id=1') == [('REJECTED',)]
    assert scalar('SELECT COUNT(*) FROM internal_postings') == 0
    assert rows("SELECT balance_cents FROM accounts WHERE account_id='A1'") == [(10000,)]


def test_f2p_other_active_reservations_for_the_payer_reduce_new_capacity():
    """A new external payment must account for another active reservation owned by the same payer."""
    seed = (
        cycle_sql('C0', '2026-08-01', 'OLD', state='COMPLETED', recon='BALANCED', close='COMPLETED')
        + cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000))
        + payment_sql(999, 'OLD-RSV', 'A1', 'B0', None, 30000, cycle='C0', seq=1, purpose='VENDOR')
        + payment_sql(1, 'S1', 'A1', 'B1', None, 25000, fee=200, tax=100)
        + "INSERT INTO reservations(payment_id,cycle_id,payer_account,amount_cents,active) VALUES(999,'C0','A1',30000,1);\n"
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert rows('SELECT outcome FROM payment_outcomes WHERE payment_id=1') == [('REJECTED',)]
    assert scalar('SELECT COUNT(*) FROM reservations WHERE payment_id=1 AND active=1') == 0


def test_f2p_blocked_internal_beneficiary_has_no_partial_financial_effect():
    """A blocked internal beneficiary must leave both account balances and all financial-effect tables untouched."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000), ('A2', 'BLOCKED', 1000))
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000, fee=100, tax=50)
        + prereq_sql()
    )
    reset_db(seed)
    before = rows('SELECT account_id,balance_cents FROM accounts ORDER BY account_id')
    run_batch()
    assert rows('SELECT account_id,balance_cents FROM accounts ORDER BY account_id') == before
    assert rows('SELECT outcome FROM payment_outcomes WHERE payment_id=1') == [('REJECTED',)]
    assert scalar('SELECT COUNT(*) FROM internal_postings') == 0
    assert scalar('SELECT COUNT(*) FROM ledger_entries') == 0


def test_f2p_resume_internal_keeps_the_existing_posting_without_reapplying_balances():
    """An authoritative internal posting must be resumed without a second payer debit or beneficiary credit."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 39850), ('A2', 'ACTIVE', 11000))
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000, fee=100, tax=50)
        + "INSERT INTO internal_postings(payment_id,cycle_id,payer_account,beneficiary_account,debit_cents,beneficiary_credit_cents) VALUES(1,'C1','A1','A2',10150,10000);\n"
        + "INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents) VALUES"
          "(1,'C1','D','CUSTOMER_CONTROL',10150),(1,'C1','C','BENEFICIARY_CONTROL',10000),"
          "(1,'C1','C','FEE_INCOME',100),(1,'C1','C','TAX_PAYABLE',50);\n"
        + prereq_sql()
    )
    reset_db(seed)
    before = rows('SELECT account_id,balance_cents FROM accounts ORDER BY account_id')
    run_batch()
    assert rows('SELECT account_id,balance_cents FROM accounts ORDER BY account_id') == before
    assert scalar('SELECT COUNT(*) FROM internal_postings WHERE payment_id=1') == 1
    assert scalar('SELECT COUNT(*) FROM ledger_entries WHERE payment_id=1') == 4


def test_f2p_resume_internal_restores_a_missing_tax_ledger_obligation():
    """A consistent resumed posting may restore missing ledger detail without repeating the financial posting."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 39850), ('A2', 'ACTIVE', 11000))
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000, fee=100, tax=50)
        + "INSERT INTO internal_postings(payment_id,cycle_id,payer_account,beneficiary_account,debit_cents,beneficiary_credit_cents) VALUES(1,'C1','A1','A2',10150,10000);\n"
        + "INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents) VALUES"
          "(1,'C1','D','CUSTOMER_CONTROL',10150),(1,'C1','C','BENEFICIARY_CONTROL',10000),(1,'C1','C','FEE_INCOME',100);\n"
        + prereq_sql()
    )
    reset_db(seed)
    before = rows('SELECT account_id,balance_cents FROM accounts ORDER BY account_id')
    run_batch()
    assert rows('SELECT account_id,balance_cents FROM accounts ORDER BY account_id') == before
    assert rows("SELECT amount_cents FROM ledger_entries WHERE payment_id=1 AND account_code='TAX_PAYABLE'") == [(50,)]
    assert reconciliation()['status'] == 'BALANCED'


def test_f2p_resume_external_keeps_one_active_reservation():
    """A partially completed external payment must reuse its active reservation rather than create another one."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000))
        + payment_sql(1, 'S1', 'A1', 'B1', None, 10000, fee=200, tax=100)
        + "INSERT INTO reservations(payment_id,cycle_id,payer_account,amount_cents,active) VALUES(1,'C1','A1',10300,1);\n"
        + "INSERT INTO clearing_items(payment_id,cycle_id,reservation_id,source_ref,amount_cents,currency,status) "
          "SELECT 1,'C1',reservation_id,'S1',10000,'INR','READY' FROM reservations WHERE payment_id=1;\n"
        + "INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents) VALUES"
          "(1,'C1','D','CUSTOMER_RESERVED',10300),(1,'C1','C','CLEARING_PAYABLE',10000),"
          "(1,'C1','C','FEE_INCOME',200),(1,'C1','C','TAX_PAYABLE',100);\n"
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert scalar('SELECT COUNT(*) FROM reservations WHERE payment_id=1 AND active=1') == 1
    assert scalar('SELECT COUNT(*) FROM clearing_items WHERE payment_id=1') == 1


def test_f2p_resume_external_can_rebuild_missing_clearing_and_ledger_state():
    """A matching active reservation is sufficient restart authority to rebuild missing clearing/ledger state once."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000))
        + payment_sql(1, 'S1', 'A1', 'B1', None, 10000, fee=200, tax=100)
        + "INSERT INTO reservations(payment_id,cycle_id,payer_account,amount_cents,active) VALUES(1,'C1','A1',10300,1);\n"
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert scalar('SELECT COUNT(*) FROM reservations WHERE payment_id=1 AND active=1') == 1
    assert rows('SELECT amount_cents,currency FROM clearing_items WHERE payment_id=1') == [(10000, 'INR')]
    assert scalar('SELECT COUNT(*) FROM ledger_entries WHERE payment_id=1') == 4
    assert reconciliation()['status'] == 'BALANCED'


def test_f2p_mismatched_external_reservation_holds_the_cycle_and_blocks_publication():
    """A resumed reservation with the wrong durable debit must hold reconciliation and all official outputs."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000))
        + payment_sql(1, 'S1', 'A1', 'B1', None, 10000, fee=200, tax=100)
        + "INSERT INTO reservations(payment_id,cycle_id,payer_account,amount_cents,active) VALUES(1,'C1','A1',9999,1);\n"
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert reconciliation()['status'] == 'HELD'
    assert rows("SELECT reconciliation_status,state FROM cycles WHERE cycle_id='C1'") == [('HELD', 'HELD')]
    assert not (OUT / 'customer_response.csv').exists()
    assert not (OUT / 'clearing_submission.csv').exists()
    assert not (OUT / 'success_authorization.json').exists()


def test_f2p_held_rerun_removes_stale_official_artifacts():
    """A held invocation must remove official files left from an earlier successful-looking attempt."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000))
        + payment_sql(1, 'S1', 'A1', 'B1', None, 10000, fee=200, tax=100)
        + "INSERT INTO reservations(payment_id,cycle_id,payer_account,amount_cents,active) VALUES(1,'C1','A1',9999,1);\n"
        + prereq_sql()
    )
    reset_db(seed)
    (OUT / 'customer_response.csv').write_text('stale\n')
    (OUT / 'clearing_submission.csv').write_text('stale\n')
    (OUT / 'success_authorization.json').write_text('{"status":"AUTHORIZED"}\n')
    run_batch()
    assert reconciliation()['status'] == 'HELD'
    for name in ('customer_response.csv', 'clearing_submission.csv', 'success_authorization.json'):
        assert not (OUT / name).exists()


def test_f2p_reconciliation_is_scoped_to_the_selected_cycle():
    """Unrelated durable state from another cycle must not contaminate the current cycle reconciliation totals."""
    seed = (
        cycle_sql('C0', '2026-08-01', 'OLD', state='COMPLETED', recon='BALANCED', close='COMPLETED')
        + cycle_sql('C1', '2026-08-08', 'RUN-1')
        + accounts_sql(('A0', 'ACTIVE', 90000), ('A1', 'ACTIVE', 50000), ('A2', 'ACTIVE', 1000))
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000, fee=100, tax=50, cycle='C1')
        + "INSERT INTO reservations(payment_id,cycle_id,payer_account,amount_cents,active) VALUES(900,'C0','A0',70000,1);\n"
        + "INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents) VALUES(900,'C0','D','CUSTOMER_RESERVED',70000),(900,'C0','C','CLEARING_PAYABLE',70000);\n"
        + prereq_sql('C1')
    )
    DB.parent.mkdir(parents=True, exist_ok=True); DB.unlink(missing_ok=True)
    shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB); con.executescript(SCHEMA.read_text()); con.execute('PRAGMA foreign_keys=OFF'); con.executescript(seed); con.commit(); con.close()
    run_batch()
    rec = reconciliation()
    assert rec['cycle_id'] == 'C1'
    assert rec['status'] == 'BALANCED'
    assert rec['reservation_count'] == 0
    assert rec['ledger_debits_cents'] == 10150
    assert rec['ledger_credits_cents'] == 10150


def test_f2p_missing_delivery_ack_blocks_completion_and_authorization():
    """Balanced publication is not enough to complete the cycle before delivery acknowledgment."""
    seed = cycle_sql() + accounts_sql(('A1', 'ACTIVE', 50000), ('A2', 'ACTIVE', 1000)) + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000) + prereq_sql(delivery=0)
    reset_db(seed); run_batch()
    assert reconciliation()['status'] == 'BALANCED'
    assert rows("SELECT completion_status FROM cycles WHERE cycle_id='C1'") == [('WAITING',)]
    assert scalar('SELECT COUNT(*) FROM success_authorizations') == 0
    assert not (OUT / 'success_authorization.json').exists()


def test_f2p_missing_report_completion_blocks_completion_and_authorization():
    """A balanced cycle must wait when reporting has not completed."""
    seed = cycle_sql() + accounts_sql(('A1', 'ACTIVE', 50000), ('A2', 'ACTIVE', 1000)) + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000) + prereq_sql(report=0)
    reset_db(seed); run_batch()
    assert reconciliation()['status'] == 'BALANCED'
    assert rows("SELECT completion_status FROM cycles WHERE cycle_id='C1'") == [('WAITING',)]
    assert scalar('SELECT COUNT(*) FROM success_authorizations') == 0


def test_f2p_missing_archive_completion_blocks_completion_and_authorization():
    """A balanced cycle must wait when archival work has not completed."""
    seed = cycle_sql() + accounts_sql(('A1', 'ACTIVE', 50000), ('A2', 'ACTIVE', 1000)) + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000) + prereq_sql(archive=0)
    reset_db(seed); run_batch()
    assert reconciliation()['status'] == 'BALANCED'
    assert rows("SELECT completion_status FROM cycles WHERE cycle_id='C1'") == [('WAITING',)]
    assert scalar('SELECT COUNT(*) FROM success_authorizations') == 0


def test_f2p_completed_rerun_preserves_exactly_one_financial_and_close_result():
    """Rerunning an already completed mixed cycle must leave every durable financial and close effect unchanged."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 100000), ('A2', 'ACTIVE', 1000), ('A3', 'ACTIVE', 100000))
        + payment_sql(1, 'I1', 'A1', 'A2', 'A2', 10000, fee=100, tax=50, seq=10)
        + payment_sql(2, 'E1', 'A3', 'B1', None, 20000, fee=200, tax=100, seq=20, purpose='VENDOR')
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    first = financial_snapshot()
    assert rows("SELECT completion_status,reconciliation_status FROM cycles WHERE cycle_id='C1'") == [('COMPLETED', 'BALANCED')]
    run_batch()
    second = financial_snapshot()
    assert second == first
    assert scalar('SELECT COUNT(*) FROM internal_postings WHERE payment_id=1') == 1
    assert scalar('SELECT COUNT(*) FROM reservations WHERE payment_id=2 AND active=1') == 1
    assert scalar('SELECT COUNT(*) FROM clearing_items WHERE payment_id=2') == 1
    assert scalar('SELECT COUNT(*) FROM success_authorizations WHERE cycle_id=\'C1\'') == 1


# ---------------------------------------------------------------------------
# P2P: stable interfaces not implicated by the incident
# ---------------------------------------------------------------------------


def test_p2p_payguard_reports_equal_values_as_consistent():
    """The existing numeric consistency helper remains available to restart logic."""
    assert compile_and_call('payguard', 'AMOUNT|10000|10000') == 'CONSISTENT'


def test_p2p_payhist_keeps_successful_business_in_accepted_history():
    """Successful outcomes continue to map to accepted source-reference history."""
    assert compile_and_call('payhist', 'SUCCESS_EXTERNAL|') == 'ACCEPTED'


def test_p2p_payhist_keeps_rejected_business_rejected():
    """Rejected outcomes continue to map to rejected source-reference history."""
    assert compile_and_call('payhist', 'REJECTED|') == 'REJECTED'
