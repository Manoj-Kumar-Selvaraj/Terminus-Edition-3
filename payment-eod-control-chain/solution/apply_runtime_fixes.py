#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    path.write_text(text.replace(old, new, 1))


common = Path('/app/eod/lib/common.sh')
replace_once(
    common,
    '''remove_gated_outputs() {
    rm -f "$OUT_DIR/customer_response.csv"
}
''',
    '''remove_gated_outputs() {
    rm -f \\
        "$OUT_DIR/customer_response.csv" \\
        "$OUT_DIR/clearing_submission.csv" \\
        "$OUT_DIR/success_authorization.json"
}
''',
    'common gated-output cleanup',
)

financial = Path('/app/eod/lib/financial.sh')
replace_once(
    financial,
    '''    payer_q="$(sql_escape "$payer_account")"
    beneficiary_q="$(sql_escape "$beneficiary_account")"
    cycle_q="$(sql_escape "$cycle_id")"

    db_exec "
''',
    '''    payer_q="$(sql_escape "$payer_account")"
    beneficiary_q="$(sql_escape "$beneficiary_account")"
    cycle_q="$(sql_escape "$cycle_id")"

    local payer_state payer_balance beneficiary_state
    payer_state="$(db_rows "SELECT status,balance_cents FROM accounts WHERE account_id='$payer_q';")"
    [[ -n "$payer_state" ]] || return 1
    IFS='|' read -r payer_state payer_balance <<< "$payer_state"
    [[ "$payer_state" == "ACTIVE" ]] || return 1
    (( $(safe_int "$payer_balance") >= total_debit )) || return 1

    beneficiary_state="$(db_scalar "SELECT COALESCE(status,'') FROM accounts WHERE account_id='$beneficiary_q';")"
    [[ "$beneficiary_state" == "ACTIVE" ]] || return 1

    db_exec "
''',
    'internal posting preconditions',
)

replace_once(
    financial,
    '''        SELECT CASE WHEN changes() = 1
            THEN 1
            ELSE RAISE(ABORT,'payer debit precondition failed')
        END;

''',
    '',
    'invalid payer RAISE expression',
)

replace_once(
    financial,
    '''        SELECT CASE WHEN changes() = 1
            THEN 1
            ELSE RAISE(ABORT,'beneficiary credit precondition failed')
        END;

''',
    '',
    'invalid beneficiary RAISE expression',
)
