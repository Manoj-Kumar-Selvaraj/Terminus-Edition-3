#!/usr/bin/env bash
set -euo pipefail

cycle_business_date() { cycle_field "$1" business_date; }
cycle_source() { cycle_field "$1" source; }
cycle_run_id() { cycle_field "$1" run_id; }

latest_reconciliation_row() {
    local c="$1"
    db_rows "
      SELECT status,original_count,outcome_count,original_value_cents,response_value_cents,
             internal_success_count,internal_posting_count,external_success_count,reservation_count,
             clearing_count,reserved_debit_cents,clearing_value_cents,external_fee_tax_cents,
             ledger_debits_cents,ledger_credits_cents,invalid_effect_count,mismatch_count,missing_ledger_count
      FROM reconciliation_runs
      WHERE cycle_id='$(sql_escape "$c")'
      ORDER BY reconciliation_id DESC LIMIT 1;"
}

payment_audit_sequence() {
    local payment_id="$1"
    db_rows "SELECT event_type FROM audit_events WHERE payment_id=$payment_id ORDER BY event_id;"
}

reservation_before_clearing_audit() {
    local payment_id="$1" reservation_event clearing_event
    reservation_event="$(db_scalar "SELECT MIN(event_id) FROM audit_events WHERE payment_id=$payment_id AND event_type='RESERVATION_CREATED';")"
    clearing_event="$(db_scalar "SELECT MIN(event_id) FROM audit_events WHERE payment_id=$payment_id AND event_type='CLEARING_CREATED';")"
    [[ -n "$reservation_event" && -n "$clearing_event" ]] || return 1
    (( reservation_event < clearing_event ))
}

all_external_audit_order_valid() {
    local c="$1" payment_id
    while IFS= read -r payment_id; do
        [[ -n "$payment_id" ]] || continue
        reservation_before_clearing_audit "$payment_id" || return 1
    done < <(db_rows "SELECT payment_id FROM payment_outcomes WHERE cycle_id='$(sql_escape "$c")' AND outcome='SUCCESS_EXTERNAL' AND reason='RESERVED_AND_QUEUED' ORDER BY payment_id;")
}

outcome_population_complete() {
    local c="$1"
    [[ "$(cycle_payment_count "$c")" == "$(cycle_outcome_count "$c")" ]]
}

successful_internal_has_posting() {
    local c="$1" n
    n="$(db_scalar "
      SELECT COUNT(*) FROM payment_outcomes o
      WHERE o.cycle_id='$(sql_escape "$c")' AND o.outcome='SUCCESS_INTERNAL'
      AND NOT EXISTS(SELECT 1 FROM internal_postings i WHERE i.payment_id=o.payment_id AND i.cycle_id=o.cycle_id);")"
    (( $(safe_int "$n") == 0 ))
}

successful_external_has_reservation() {
    local c="$1" n
    n="$(db_scalar "
      SELECT COUNT(*) FROM payment_outcomes o
      WHERE o.cycle_id='$(sql_escape "$c")' AND o.outcome='SUCCESS_EXTERNAL'
      AND NOT EXISTS(SELECT 1 FROM reservations r WHERE r.payment_id=o.payment_id AND r.cycle_id=o.cycle_id AND r.active=1);")"
    (( $(safe_int "$n") == 0 ))
}

successful_external_has_clearing() {
    local c="$1" n
    n="$(db_scalar "
      SELECT COUNT(*) FROM payment_outcomes o
      WHERE o.cycle_id='$(sql_escape "$c")' AND o.outcome='SUCCESS_EXTERNAL'
      AND NOT EXISTS(SELECT 1 FROM clearing_items x WHERE x.payment_id=o.payment_id AND x.cycle_id=o.cycle_id);")"
    (( $(safe_int "$n") == 0 ))
}

non_success_has_no_effect() {
    local c="$1"
    (( $(safe_int "$(financial_effect_on_non_success_count "$c")") == 0 ))
}

publication_matches_cycle_status() {
    local c="$1" reconciliation completion
    reconciliation="$(reconciliation_status_for_cycle "$c")"
    completion="$(completion_status_for_cycle "$c")"
    if [[ "$reconciliation" != BALANCED ]]; then
        [[ ! -e "$OUT_DIR/customer_response.csv" && ! -e "$OUT_DIR/clearing_submission.csv" && ! -e "$OUT_DIR/success_authorization.json" ]]
        return
    fi
    [[ -f "$OUT_DIR/customer_response.csv" && -f "$OUT_DIR/clearing_submission.csv" ]] || return 1
    if [[ "$completion" == COMPLETED ]]; then [[ -f "$OUT_DIR/success_authorization.json" ]]; else [[ ! -f "$OUT_DIR/success_authorization.json" ]]; fi
}

cycle_operational_health() {
    local c="$1" failures=0
    outcome_population_complete "$c" || failures=$((failures+1))
    successful_internal_has_posting "$c" || failures=$((failures+1))
    successful_external_has_reservation "$c" || failures=$((failures+1))
    successful_external_has_clearing "$c" || failures=$((failures+1))
    printf '%s' "$failures"
}

write_payment_state_csv() {
    local c="$1"
    db_csv "
      SELECT p.payment_id,p.source_ref,p.payer_account,p.beneficiary_ref,
             CASE WHEN p.beneficiary_account IS NULL THEN 'EXTERNAL' ELSE 'INTERNAL' END AS route_kind,
             COALESCE(o.outcome,'UNDECIDED') AS outcome,
             COALESCE(o.execution_state,'') AS execution_state,
             CASE WHEN i.payment_id IS NULL THEN 0 ELSE 1 END AS posting_present,
             CASE WHEN r.payment_id IS NULL THEN 0 ELSE 1 END AS active_reservation_present,
             CASE WHEN x.payment_id IS NULL THEN 0 ELSE 1 END AS clearing_present
      FROM payments p
      LEFT JOIN payment_outcomes o ON o.payment_id=p.payment_id
      LEFT JOIN internal_postings i ON i.payment_id=p.payment_id
      LEFT JOIN reservations r ON r.payment_id=p.payment_id AND r.active=1
      LEFT JOIN clearing_items x ON x.payment_id=p.payment_id
      WHERE p.cycle_id='$(sql_escape "$c")'
      ORDER BY p.received_seq,p.payment_id;" > "$OUT_DIR/payment_state.csv"
}

write_audit_timeline_csv() {
    local c="$1"
    db_csv "
      SELECT event_id,cycle_id,COALESCE(payment_id,'') AS payment_id,event_type,event_key,event_detail,recorded_at
      FROM audit_events WHERE cycle_id='$(sql_escape "$c")' ORDER BY event_id;" > "$OUT_DIR/audit_timeline.csv"
}

write_checkpoint_csv() {
    local c="$1"
    db_csv "
      SELECT checkpoint_id,cycle_id,COALESCE(payment_id,'') AS payment_id,stage,status,checkpoint_key,recorded_at
      FROM work_checkpoints WHERE cycle_id='$(sql_escape "$c")' ORDER BY checkpoint_id;" > "$OUT_DIR/checkpoints.csv"
}

write_operations_summary() {
    local c="$1" latest health
    latest="$(latest_reconciliation_row "$c")"
    health="$(cycle_operational_health "$c")"
    jq -n \
      --arg cycle_id "$c" \
      --arg business_date "$(cycle_business_date "$c")" \
      --arg source "$(cycle_source "$c")" \
      --arg run_id "$(cycle_run_id "$c")" \
      --arg state "$(cycle_state_for_cycle "$c")" \
      --arg reconciliation_status "$(reconciliation_status_for_cycle "$c")" \
      --arg completion_status "$(completion_status_for_cycle "$c")" \
      --argjson operational_failures "$(safe_int "$health")" \
      --arg latest_reconciliation "$latest" \
      '{cycle_id:$cycle_id,business_date:$business_date,source:$source,run_id:$run_id,
        state:$state,reconciliation_status:$reconciliation_status,completion_status:$completion_status,
        operational_failures:$operational_failures,latest_reconciliation:$latest_reconciliation}' \
      > "$OUT_DIR/operations_summary.json"
}

write_operational_artifacts() {
    local c="$1"
    write_payment_state_csv "$c"
    write_audit_timeline_csv "$c"
    write_checkpoint_csv "$c"
    write_restart_report "$c"
    write_capacity_report "$c"
    population_summary_json "$c" > "$OUT_DIR/population_report.json"
    accounting_summary_json "$c" > "$OUT_DIR/accounting_report.json"
    lifecycle_summary_json "$c" > "$OUT_DIR/lifecycle_report.json"
    write_operations_summary "$c"
}
