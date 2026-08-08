#!/usr/bin/env bash
set -euo pipefail

cycle_payment_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")';"; }
cycle_outcome_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM payment_outcomes WHERE cycle_id='$(sql_escape "$c")';"; }
cycle_internal_success_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM payment_outcomes WHERE cycle_id='$(sql_escape "$c")' AND outcome='SUCCESS_INTERNAL';"; }
cycle_external_success_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM payment_outcomes WHERE cycle_id='$(sql_escape "$c")' AND outcome='SUCCESS_EXTERNAL';"; }
cycle_duplicate_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM payment_outcomes WHERE cycle_id='$(sql_escape "$c")' AND outcome='DUPLICATE';"; }
cycle_rejected_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM payment_outcomes WHERE cycle_id='$(sql_escape "$c")' AND outcome='REJECTED';"; }
cycle_active_reservation_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM reservations WHERE cycle_id='$(sql_escape "$c")' AND active=1;"; }
cycle_clearing_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM clearing_items WHERE cycle_id='$(sql_escape "$c")';"; }
cycle_internal_posting_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM internal_postings WHERE cycle_id='$(sql_escape "$c")';"; }
cycle_ledger_count() { local c="$1"; db_scalar "SELECT COUNT(*) FROM ledger_entries WHERE cycle_id='$(sql_escape "$c")';"; }

orphan_outcome_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payment_outcomes o LEFT JOIN payments p ON p.payment_id=o.payment_id WHERE o.cycle_id='$(sql_escape "$c")' AND (p.payment_id IS NULL OR p.cycle_id<>o.cycle_id);"
}
orphan_posting_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM internal_postings i LEFT JOIN payments p ON p.payment_id=i.payment_id WHERE i.cycle_id='$(sql_escape "$c")' AND (p.payment_id IS NULL OR p.cycle_id<>i.cycle_id);"
}
orphan_reservation_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM reservations r LEFT JOIN payments p ON p.payment_id=r.payment_id WHERE r.cycle_id='$(sql_escape "$c")' AND (p.payment_id IS NULL OR p.cycle_id<>r.cycle_id);"
}
orphan_clearing_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM clearing_items x LEFT JOIN payments p ON p.payment_id=x.payment_id WHERE x.cycle_id='$(sql_escape "$c")' AND (p.payment_id IS NULL OR p.cycle_id<>x.cycle_id);"
}
orphan_ledger_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM ledger_entries l LEFT JOIN payments p ON p.payment_id=l.payment_id WHERE l.cycle_id='$(sql_escape "$c")' AND (p.payment_id IS NULL OR p.cycle_id<>l.cycle_id);"
}

multiple_internal_posting_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM (SELECT payment_id FROM internal_postings WHERE cycle_id='$(sql_escape "$c")' GROUP BY payment_id HAVING COUNT(*)>1);"
}
multiple_active_reservation_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM (SELECT payment_id FROM reservations WHERE cycle_id='$(sql_escape "$c")' AND active=1 GROUP BY payment_id HAVING COUNT(*)>1);"
}
multiple_clearing_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM (SELECT payment_id FROM clearing_items WHERE cycle_id='$(sql_escape "$c")' GROUP BY payment_id HAVING COUNT(*)>1);"
}
multiple_authorization_count() {
    local c="$1"
    db_scalar "SELECT CASE WHEN COUNT(*)>1 THEN 1 ELSE 0 END FROM success_authorizations WHERE cycle_id='$(sql_escape "$c")';"
}

clearing_without_active_reservation_count() {
    local c="$1"
    db_scalar "
        SELECT COUNT(*) FROM clearing_items x
        WHERE x.cycle_id='$(sql_escape "$c")'
          AND NOT EXISTS(
            SELECT 1 FROM reservations r
            WHERE r.reservation_id=x.reservation_id
              AND r.payment_id=x.payment_id
              AND r.cycle_id=x.cycle_id
              AND r.active=1
          );"
}
reservation_amount_mismatch_count() {
    local c="$1"
    db_scalar "
        SELECT COUNT(*) FROM reservations r JOIN payments p ON p.payment_id=r.payment_id
        WHERE r.cycle_id='$(sql_escape "$c")' AND r.active=1
          AND r.amount_cents<>(p.amount_cents+p.fee_cents+p.tax_cents);"
}
clearing_amount_mismatch_count() {
    local c="$1"
    db_scalar "
        SELECT COUNT(*) FROM clearing_items x JOIN payments p ON p.payment_id=x.payment_id
        WHERE x.cycle_id='$(sql_escape "$c")'
          AND (x.amount_cents<>p.amount_cents OR x.currency<>p.currency);"
}
internal_posting_amount_mismatch_count() {
    local c="$1"
    db_scalar "
        SELECT COUNT(*) FROM internal_postings i JOIN payments p ON p.payment_id=i.payment_id
        WHERE i.cycle_id='$(sql_escape "$c")'
          AND (i.debit_cents<>(p.amount_cents+p.fee_cents+p.tax_cents) OR i.beneficiary_credit_cents<>p.amount_cents);"
}
financial_effect_on_non_success_count() {
    local c="$1"
    db_scalar "
        SELECT COUNT(*) FROM payment_outcomes o
        WHERE o.cycle_id='$(sql_escape "$c")' AND o.outcome IN ('DUPLICATE','REJECTED')
          AND (
             EXISTS(SELECT 1 FROM internal_postings i WHERE i.payment_id=o.payment_id)
             OR EXISTS(SELECT 1 FROM reservations r WHERE r.payment_id=o.payment_id AND r.active=1)
             OR EXISTS(SELECT 1 FROM clearing_items x WHERE x.payment_id=o.payment_id)
             OR EXISTS(SELECT 1 FROM ledger_entries l WHERE l.payment_id=o.payment_id)
          );"
}
held_execution_state_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payment_outcomes WHERE cycle_id='$(sql_escape "$c")' AND execution_state LIKE 'HELD_%';"
}
ledger_duplicate_key_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM (SELECT payment_id,side,account_code FROM ledger_entries WHERE cycle_id='$(sql_escape "$c")' GROUP BY payment_id,side,account_code HAVING COUNT(*)>1);"
}
ledger_zero_amount_noise_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM ledger_entries WHERE cycle_id='$(sql_escape "$c")' AND amount_cents=0 AND account_code NOT IN ('FEE_INCOME','TAX_PAYABLE');"
}
ledger_unbalanced_payment_count() {
    local c="$1"
    db_scalar "
        SELECT COUNT(*) FROM (
          SELECT payment_id,
                 SUM(CASE WHEN side='D' THEN amount_cents ELSE 0 END) AS d,
                 SUM(CASE WHEN side='C' THEN amount_cents ELSE 0 END) AS cr
          FROM ledger_entries WHERE cycle_id='$(sql_escape "$c")'
          GROUP BY payment_id HAVING d<>cr
        );"
}
history_current_cycle_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payment_history WHERE accepted_cycle_id='$(sql_escape "$c")';"
}
payment_without_checkpoint_count() {
    local c="$1"
    db_scalar "
        SELECT COUNT(*) FROM payments p
        WHERE p.cycle_id='$(sql_escape "$c")'
          AND NOT EXISTS(
            SELECT 1 FROM work_checkpoints w
            WHERE w.cycle_id=p.cycle_id AND w.payment_id=p.payment_id
              AND w.stage='PAYMENT' AND w.status='DONE'
          );"
}
missing_financial_audit_count() {
    local c="$1"
    db_scalar "
        SELECT COUNT(*) FROM payment_outcomes o
        WHERE o.cycle_id='$(sql_escape "$c")'
          AND o.outcome IN ('SUCCESS_INTERNAL','SUCCESS_EXTERNAL')
          AND NOT EXISTS(
            SELECT 1 FROM audit_events a
            WHERE a.cycle_id=o.cycle_id AND a.payment_id=o.payment_id
              AND a.event_type IN ('INTERNAL_POSTED','INTERNAL_RESUMED','RESERVATION_CREATED','EXTERNAL_RESUMED')
          );"
}

assert_cycle_relational_integrity() {
    local c="$1"
    local failures=0 label value
    while IFS='|' read -r label value; do
        value="$(safe_int "$value")"
        if (( value != 0 )); then
            printf 'integrity failure: %s=%s\n' "$label" "$value" >&2
            failures=$((failures+1))
        fi
    done <<METRICS
orphan_outcomes|$(orphan_outcome_count "$c")
orphan_postings|$(orphan_posting_count "$c")
orphan_reservations|$(orphan_reservation_count "$c")
orphan_clearing|$(orphan_clearing_count "$c")
orphan_ledger|$(orphan_ledger_count "$c")
multiple_internal_postings|$(multiple_internal_posting_count "$c")
multiple_clearing|$(multiple_clearing_count "$c")
multiple_authorizations|$(multiple_authorization_count "$c")
clearing_amount_mismatch|$(clearing_amount_mismatch_count "$c")
internal_posting_mismatch|$(internal_posting_amount_mismatch_count "$c")
financial_effect_on_non_success|$(financial_effect_on_non_success_count "$c")
ledger_zero_noise|$(ledger_zero_amount_noise_count "$c")
ledger_unbalanced_payment|$(ledger_unbalanced_payment_count "$c")
METRICS
    (( failures == 0 ))
}

cycle_integrity_summary_json() {
    local c="$1"
    jq -n \
      --arg cycle_id "$c" \
      --argjson payments "$(safe_int "$(cycle_payment_count "$c")")" \
      --argjson outcomes "$(safe_int "$(cycle_outcome_count "$c")")" \
      --argjson internal_success "$(safe_int "$(cycle_internal_success_count "$c")")" \
      --argjson external_success "$(safe_int "$(cycle_external_success_count "$c")")" \
      --argjson duplicate "$(safe_int "$(cycle_duplicate_count "$c")")" \
      --argjson rejected "$(safe_int "$(cycle_rejected_count "$c")")" \
      --argjson internal_postings "$(safe_int "$(cycle_internal_posting_count "$c")")" \
      --argjson reservations "$(safe_int "$(cycle_active_reservation_count "$c")")" \
      --argjson clearing "$(safe_int "$(cycle_clearing_count "$c")")" \
      --argjson ledger_entries "$(safe_int "$(cycle_ledger_count "$c")")" \
      --argjson held_execution_states "$(safe_int "$(held_execution_state_count "$c")")" \
      --argjson current_cycle_history "$(safe_int "$(history_current_cycle_count "$c")")" \
      --argjson payments_without_checkpoint "$(safe_int "$(payment_without_checkpoint_count "$c")")" \
      --argjson missing_financial_audit "$(safe_int "$(missing_financial_audit_count "$c")")" \
      '{cycle_id:$cycle_id,payments:$payments,outcomes:$outcomes,internal_success:$internal_success,
        external_success:$external_success,duplicate:$duplicate,rejected:$rejected,
        internal_postings:$internal_postings,active_reservations:$reservations,clearing_items:$clearing,
        ledger_entries:$ledger_entries,held_execution_states:$held_execution_states,
        current_cycle_history:$current_cycle_history,payments_without_checkpoint:$payments_without_checkpoint,
        missing_financial_audit:$missing_financial_audit}'
}
