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
    '''post_execution_integrity() {
    local c="$1"
    stage_begin "$c" INTEGRITY
    local orphan_rows
    orphan_rows=$((
        $(safe_int "$(orphan_outcome_count "$c")") +
        $(safe_int "$(orphan_posting_count "$c")") +
        $(safe_int "$(orphan_reservation_count "$c")") +
        $(safe_int "$(orphan_clearing_count "$c")") +
        $(safe_int "$(orphan_ledger_count "$c")")
    ))
    if (( orphan_rows == 0 )); then stage_done "$c" INTEGRITY; return 0; fi
    stage_held "$c" INTEGRITY "durable payment state is internally inconsistent"
    return 1
}
''',
    '''post_execution_integrity() {
    local c="$1"
    stage_begin "$c" INTEGRITY
    if assert_cycle_relational_integrity "$c" && cycle_accounting_contract_valid "$c"; then stage_done "$c" INTEGRITY; return 0; fi
    stage_held "$c" INTEGRITY "durable payment state is internally inconsistent"
    return 1
}
''',
    'full post-execution integrity',
)
replace_once(
    control,
    '''    local expected_outcomes actual_outcomes
    expected_outcomes="$(cycle_payment_count "$c")"
    actual_outcomes="$(cycle_outcome_count "$c")"
    if (( $(safe_int "$actual_outcomes") < $(safe_int "$expected_outcomes") )); then
''',
    '''    if held_execution_outcomes_present "$c"; then
''',
    'held execution state reconciliation guard',
)
replace_once(
    control,
    '''    reconcile_cycle_after_execution "$c" || true
    if ! publish_cycle_after_reconciliation "$c"; then write_control_snapshot "$c"; return 1; fi
''',
    '''    if ! reconcile_cycle_after_execution "$c"; then
        remove_gated_outputs
        write_control_snapshot "$c"
        return 1
    fi
    if ! publish_cycle_after_reconciliation "$c"; then write_control_snapshot "$c"; return 1; fi
''',
    'reconciliation failure propagation',
)
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

restart = Path('/app/eod/lib/restart.sh')
replace_once(
    restart,
    '''    state="$(payment_durable_state "$payment_id")"
    IFS='|' read -r posting reservation clearing ledger outcome checkpoint <<< "$state"

    if [[ "$kind" == INTERNAL ]]; then
''',
    '''    state="$(payment_durable_state "$payment_id")"
    IFS='|' read -r posting reservation clearing ledger outcome checkpoint <<< "$state"

    if payment_has_conflicting_effect_families "$payment_id"; then printf CONFLICTING_EFFECTS; return; fi
    if [[ "$kind" == INTERNAL ]]; then
''',
    'conflicting restart effects',
)
replace_once(
    restart,
    '''    if (( $(safe_int "$reservation") > 0 )); then
        printf RESUME_EXTERNAL
    elif (( $(safe_int "$clearing") > 0 )); then
''',
    '''    if (( $(safe_int "$reservation") > 0 )); then
        if ! external_reservation_consistent "$payment_id"; then printf INCONSISTENT_EXTERNAL; return; fi
        if (( $(safe_int "$clearing") > 0 )) && ! external_clearing_consistent "$payment_id"; then printf INCONSISTENT_EXTERNAL; return; fi
        printf RESUME_EXTERNAL
    elif (( $(safe_int "$clearing") > 0 )); then
''',
    'external restart consistency',
)

lifecycle = Path('/app/eod/lib/lifecycle.sh')
replace_once(
    lifecycle,
    '''    publication_stage_consistent "$c" || failures=$((failures+1))
    close_stage_consistent "$c" || failures=$((failures+1))
    printf '%s' "$failures"
''',
    '''    publication_stage_consistent "$c" || failures=$((failures+1))
    close_stage_consistent "$c" || failures=$((failures+1))
    completion_audit_consistent "$c" || failures=$((failures+1))
    publication_audit_consistent "$c" || failures=$((failures+1))
    printf '%s' "$failures"
''',
    'lifecycle audit completeness',
)

operations = Path('/app/eod/lib/operations.sh')
replace_once(
    operations,
    '''    successful_internal_has_posting "$c" || failures=$((failures+1))
    successful_external_has_reservation "$c" || failures=$((failures+1))
    successful_external_has_clearing "$c" || failures=$((failures+1))
    printf '%s' "$failures"
''',
    '''    successful_internal_has_posting "$c" || failures=$((failures+1))
    successful_external_has_reservation "$c" || failures=$((failures+1))
    successful_external_has_clearing "$c" || failures=$((failures+1))
    non_success_has_no_effect "$c" || failures=$((failures+1))
    assert_cycle_relational_integrity "$c" || failures=$((failures+1))
    printf '%s' "$failures"
''',
    'operational integrity completeness',
)

reconcile = Path('/app/eod/lib/reconcile.sh')
replace_once(
    reconcile,
    '''    RESERVED_DEBIT="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM reservations
        WHERE active=1;
    ")"
''',
    '''    RESERVED_DEBIT="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM reservations
        WHERE cycle_id='$(sql_escape "$cycle_id")'
          AND active=1;
    ")"
''',
    'cycle-scoped reserved debit',
)
replace_once(
    reconcile,
    '''    CLEARING_VALUE="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM clearing_items;
    ")"
''',
    '''    CLEARING_VALUE="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM clearing_items
        WHERE cycle_id='$(sql_escape "$cycle_id")';
    ")"
''',
    'cycle-scoped clearing value',
)
replace_once(
    reconcile,
    '''    LEDGER_DEBITS="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM ledger_entries
        WHERE side='D';
    ")"
''',
    '''    LEDGER_DEBITS="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM ledger_entries
        WHERE cycle_id='$(sql_escape "$cycle_id")'
          AND side='D';
    ")"
''',
    'cycle-scoped ledger debits',
)
replace_once(
    reconcile,
    '''    LEDGER_CREDITS="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM ledger_entries
        WHERE side='C';
    ")"
''',
    '''    LEDGER_CREDITS="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM ledger_entries
        WHERE cycle_id='$(sql_escape "$cycle_id")'
          AND side='C';
    ")"
''',
    'cycle-scoped ledger credits',
)
replace_once(
    reconcile,
    '''    INVALID_EFFECT_COUNT="$(metric_scalar "
        SELECT COUNT(*)
        FROM payment_outcomes o
        WHERE o.cycle_id='$(sql_escape "$cycle_id")'
          AND o.outcome IN ('DUPLICATE','REJECTED')
          AND EXISTS(SELECT 1 FROM internal_postings i WHERE i.payment_id=o.payment_id);
    ")"
''',
    '''    INVALID_EFFECT_COUNT="$(count_invalid_financial_effects "$cycle_id")"
''',
    'all invalid financial effects',
)
replace_once(
    reconcile,
    '''    MISMATCH_COUNT="$(metric_scalar "
        SELECT COUNT(*)
        FROM clearing_items x
        WHERE x.cycle_id='$(sql_escape "$cycle_id")'
          AND NOT EXISTS(
              SELECT 1 FROM reservations r
              WHERE r.reservation_id=x.reservation_id
                AND r.payment_id=x.payment_id
                AND r.active=1
          );
    ")"
''',
    '''    MISMATCH_COUNT=$((ext_mismatch + int_mismatch))
''',
    'complete financial mismatch count',
)
replace_once(
    reconcile,
    '''    MISSING_LEDGER_COUNT="$(metric_scalar "
        SELECT COUNT(*)
        FROM payment_outcomes o
        WHERE o.cycle_id='$(sql_escape "$cycle_id")'
          AND o.outcome IN ('SUCCESS_INTERNAL','SUCCESS_EXTERNAL')
          AND NOT EXISTS(SELECT 1 FROM ledger_entries l WHERE l.payment_id=o.payment_id);
    ")"
''',
    '''    MISSING_LEDGER_COUNT="$(count_missing_ledger "$cycle_id")"
''',
    'complete missing ledger count',
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
