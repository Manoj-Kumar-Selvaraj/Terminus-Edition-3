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

close = Path('/app/eod/lib/close.sh')
replace_once(
    close,
    '''close_cycle() {
    local c="$1" decision
    record_delivery_ack_event "$c"
    decision="$(close_decision "$c")"
    if [[ "$decision" == COMPLETE ]] && complete_cycle_once "$c"; then
        create_authorization_once "$c"
        return 0
    fi
    mark_cycle_waiting "$c"
    remove_authorization_when_incomplete "$c"
    return 1
}
''',
    '''close_cycle() {
    local c="$1" decision
    record_delivery_ack_event "$c"
    decision="$(close_decision "$c")"

    if [[ "$decision" != COMPLETE ]]; then
        mark_cycle_waiting "$c"
        remove_authorization_when_incomplete "$c"
        return 1
    fi

    if complete_cycle_once "$c"; then
        create_authorization_once "$c"
        return 0
    fi

    mark_cycle_waiting "$c"
    remove_authorization_when_incomplete "$c"
    return 1
}
''',
    'balanced cycle waiting transition',
)

control = Path('/app/eod/lib/control.sh')
replace_once(
    control,
    '''    if ! publish_cycle_after_reconciliation "$c"; then write_control_snapshot "$c"; return 1; fi
    close_cycle_after_publication "$c" || true
    write_control_snapshot "$c"
''',
    '''    if ! publish_cycle_after_reconciliation "$c"; then write_control_snapshot "$c"; return 1; fi
    close_cycle_after_publication "$c" || true
    if [[ "$(reconciliation_status_for_cycle "$c")" == BALANCED && "$(completion_status_for_cycle "$c")" != COMPLETED ]]; then
        mark_cycle_waiting "$c"
    fi
    write_control_snapshot "$c"
''',
    'balanced incomplete controller lifecycle',
)

publish = Path('/app/eod/lib/publish.sh')
replace_once(
    publish,
    '''write_response_staging() { local c="$1" p="$2"; db_csv "$(response_query "$c")" > "$p"; }
write_clearing_staging() { local c="$1" p="$2"; db_csv "$(clearing_query "$c")" > "$p"; }
''',
    '''write_response_staging() {
    local c="$1" p="$2"
    printf 'payment_id,source_ref,outcome,reason\\n' > "$p"
    "$SQLITE_BIN" -noheader -csv "$DB" "$(response_query "$c")" >> "$p"
}
write_clearing_staging() {
    local c="$1" p="$2"
    printf 'payment_id,source_ref,amount_cents,currency\\n' > "$p"
    "$SQLITE_BIN" -noheader -csv "$DB" "$(clearing_query "$c")" >> "$p"
}
''',
    'deterministic publication headers for empty result sets',
)
