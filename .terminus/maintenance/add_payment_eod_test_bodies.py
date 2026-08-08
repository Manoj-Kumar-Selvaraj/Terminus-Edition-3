#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / 'payment-eod-control-chain' / 'tests' / 'test_outputs.py'
text = path.read_text(encoding='utf-8')
marker = '''# ---------------------------------------------------------------------------
# P2P: stable interfaces not implicated by the incident
# ---------------------------------------------------------------------------
'''
expected_absent = [
    'test_f2p_current_cycle_history_is_restart_state_not_cross_cycle_replay',
    'test_f2p_inconsistent_internal_posting_holds_the_cycle',
    'test_f2p_inconsistent_existing_clearing_holds_the_cycle',
    'test_p2p_accepted_source_from_an_earlier_cycle_is_suppressed_as_replay',
    'test_p2p_blocked_payer_is_rejected_without_financial_effect',
    'test_p2p_balanced_cycle_keeps_the_documented_official_output_shape',
]
if any(name in text for name in expected_absent):
    raise SystemExit('one or more planned verifier bodies already exist; reconcile before applying')
if text.count(marker) != 1:
    raise SystemExit(f'expected one P2P marker, found {text.count(marker)}')

f2p = r'''

def test_f2p_current_cycle_history_is_restart_state_not_cross_cycle_replay():
    """History accepted by the current cycle must be restart state rather than prior replay evidence."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000), ('A2', 'ACTIVE', 1000))
        + history_sql('S1', 'A1', 'A2', 10000, status='ACCEPTED', cycle='C1')
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000)
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert rows("SELECT outcome FROM payment_outcomes WHERE payment_id=1") == [('SUCCESS_INTERNAL',)]
    assert scalar('SELECT COUNT(*) FROM internal_postings WHERE payment_id=1') == 1


def test_f2p_inconsistent_internal_posting_holds_the_cycle():
    """A durable internal posting with the wrong debit must hold instead of being replayed or accepted."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 39850), ('A2', 'ACTIVE', 11000))
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000, fee=100, tax=50)
        + "INSERT INTO internal_postings(payment_id,cycle_id,payer_account,beneficiary_account,debit_cents,beneficiary_credit_cents) VALUES(1,'C1','A1','A2',9999,10000);\n"
        + "INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents) VALUES"
          "(1,'C1','D','CUSTOMER_CONTROL',10150),(1,'C1','C','BENEFICIARY_CONTROL',10000),"
          "(1,'C1','C','FEE_INCOME',100),(1,'C1','C','TAX_PAYABLE',50);\n"
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert reconciliation()['status'] == 'HELD'
    assert rows("SELECT reconciliation_status,state FROM cycles WHERE cycle_id='C1'") == [('HELD', 'HELD')]
    assert not (OUT / 'customer_response.csv').exists()
    assert not (OUT / 'clearing_submission.csv').exists()


def test_f2p_inconsistent_existing_clearing_holds_the_cycle():
    """A resumed external payment must hold when its existing clearing amount disagrees with principal."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000))
        + payment_sql(1, 'S1', 'A1', 'B1', None, 10000, fee=200, tax=100)
        + "INSERT INTO reservations(payment_id,cycle_id,payer_account,amount_cents,active) VALUES(1,'C1','A1',10300,1);\n"
        + "INSERT INTO clearing_items(payment_id,cycle_id,reservation_id,source_ref,amount_cents,currency,status) "
          "SELECT 1,'C1',reservation_id,'S1',9999,'INR','READY' FROM reservations WHERE payment_id=1;\n"
        + "INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents) VALUES"
          "(1,'C1','D','CUSTOMER_RESERVED',10300),(1,'C1','C','CLEARING_PAYABLE',10000),"
          "(1,'C1','C','FEE_INCOME',200),(1,'C1','C','TAX_PAYABLE',100);\n"
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert reconciliation()['status'] == 'HELD'
    assert rows("SELECT reconciliation_status,state FROM cycles WHERE cycle_id='C1'") == [('HELD', 'HELD')]
    assert not (OUT / 'customer_response.csv').exists()
    assert not (OUT / 'clearing_submission.csv').exists()


'''

p2p = r'''

def test_p2p_accepted_source_from_an_earlier_cycle_is_suppressed_as_replay():
    """An accepted source reference from an earlier cycle remains a duplicate with no financial effect."""
    seed = (
        cycle_sql('C0', '2026-08-01', 'OLD', state='COMPLETED', recon='BALANCED', close='COMPLETED')
        + cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000), ('A2', 'ACTIVE', 1000))
        + history_sql('S1', 'A1', 'A2', 10000, status='ACCEPTED', cycle='C0')
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000)
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert rows("SELECT outcome FROM payment_outcomes WHERE payment_id=1") == [('DUPLICATE',)]
    assert scalar('SELECT COUNT(*) FROM internal_postings WHERE payment_id=1') == 0
    assert scalar('SELECT COUNT(*) FROM reservations WHERE payment_id=1 AND active=1') == 0
    assert scalar('SELECT COUNT(*) FROM ledger_entries WHERE payment_id=1') == 0


def test_p2p_blocked_payer_is_rejected_without_financial_effect():
    """The payer eligibility guard must continue rejecting a blocked debit account without partial state."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'BLOCKED', 50000), ('A2', 'ACTIVE', 1000))
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000)
        + prereq_sql()
    )
    reset_db(seed)
    before = rows('SELECT account_id,balance_cents FROM accounts ORDER BY account_id')
    run_batch()
    assert rows('SELECT account_id,balance_cents FROM accounts ORDER BY account_id') == before
    assert rows("SELECT outcome FROM payment_outcomes WHERE payment_id=1") == [('REJECTED',)]
    assert scalar('SELECT COUNT(*) FROM internal_postings') == 0
    assert scalar('SELECT COUNT(*) FROM ledger_entries') == 0


def test_p2p_balanced_cycle_keeps_the_documented_official_output_shape():
    """A simple balanced internal cycle must keep the documented response, clearing, and authorization interfaces."""
    seed = (
        cycle_sql()
        + accounts_sql(('A1', 'ACTIVE', 50000), ('A2', 'ACTIVE', 1000))
        + payment_sql(1, 'S1', 'A1', 'A2', 'A2', 10000)
        + prereq_sql()
    )
    reset_db(seed)
    run_batch()
    assert (OUT / 'customer_response.csv').read_text().splitlines()[0] == 'payment_id,source_ref,outcome,reason'
    response = read_csv(OUT / 'customer_response.csv')
    assert len(response) == 1
    assert response[0]['payment_id'] == '1'
    assert response[0]['source_ref'] == 'S1'
    assert response[0]['outcome'] == 'SUCCESS_INTERNAL'
    assert (OUT / 'clearing_submission.csv').read_text().splitlines() == ['payment_id,source_ref,amount_cents,currency']
    authorization = json.loads((OUT / 'success_authorization.json').read_text())
    assert authorization['cycle_id'] == 'C1'
    assert authorization['status'] == 'AUTHORIZED'


'''

path.write_text(text.replace(marker, f2p + marker + p2p, 1), encoding='utf-8')
