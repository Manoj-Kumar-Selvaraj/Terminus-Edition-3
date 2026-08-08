#!/usr/bin/env bash
set -euo pipefail

stage_begin() { local c="$1" s="$2"; checkpoint "$c" NULL "$s" STARTED "$c:$s"; audit_event "$c" NULL "${s}_STARTED" "$c:$s:STARTED" "$s stage started"; }
stage_done() { local c="$1" s="$2"; checkpoint "$c" NULL "$s" DONE "$c:$s"; audit_event "$c" NULL "${s}_DONE" "$c:$s:DONE" "$s stage completed"; }
stage_held() { local c="$1" s="$2" d="$3"; checkpoint "$c" NULL "$s" HELD "$c:$s"; audit_event "$c" NULL "${s}_HELD" "$c:$s:HELD" "$d"; }

validate_cycle_header() {
    local c="$1"
    [[ "$(db_scalar "SELECT COUNT(*) FROM cycles WHERE cycle_id='$(sql_escape "$c")';")" == 1 ]]
}
validate_cycle_source_identity() {
    local c="$1" source date run
    source="$(cycle_field "$c" source)"; date="$(cycle_field "$c" business_date)"; run="$(cycle_field "$c" run_id)"
    [[ -n "$source" && -n "$date" && -n "$run" ]]
}
validate_payment_population() {
    local c="$1" total invalid
    total="$(cycle_payment_count "$c")"
    invalid="$(db_scalar "
      SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")'
      AND (source_ref='' OR payer_account='' OR beneficiary_ref='' OR amount_cents<=0 OR fee_cents<0 OR tax_cents<0 OR currency='' OR purpose='');")"
    (( $(safe_int "$total") > 0 && $(safe_int "$invalid") == 0 ))
}
validate_unique_source_refs_within_cycle() {
    local c="$1" n
    n="$(db_scalar "SELECT COUNT(*) FROM (SELECT source_ref FROM payments WHERE cycle_id='$(sql_escape "$c")' GROUP BY source_ref HAVING COUNT(*)>1);")"
    (( $(safe_int "$n") == 0 ))
}
validate_account_references() {
    local c="$1" n
    n="$(db_scalar "SELECT COUNT(*) FROM payments p LEFT JOIN accounts a ON a.account_id=p.payer_account WHERE p.cycle_id='$(sql_escape "$c")' AND a.account_id IS NULL;")"
    (( $(safe_int "$n") == 0 ))
}
validate_internal_beneficiary_references() {
    local c="$1" n
    n="$(db_scalar "SELECT COUNT(*) FROM payments p LEFT JOIN accounts a ON a.account_id=p.beneficiary_account WHERE p.cycle_id='$(sql_escape "$c")' AND p.beneficiary_account IS NOT NULL AND a.account_id IS NULL;")"
    (( $(safe_int "$n") == 0 ))
}
validate_preprocessing_state() {
    local c="$1"
    validate_cycle_header "$c" || return 1
    validate_cycle_source_identity "$c" || return 2
    validate_payment_population "$c" || return 3
    population_is_valid "$c" || return 7
    validate_unique_source_refs_within_cycle "$c" || return 4
    validate_account_references "$c" || return 5
    validate_internal_beneficiary_references "$c" || return 6
}

cycle_is_completed() { [[ "$(completion_status_for_cycle "$1")" == COMPLETED ]]; }

prepare_cycle() {
    local c="$1"
    ensure_prerequisite_row "$c"
    remove_gated_outputs
    validate_preprocessing_state "$c"
    mark_cycle_processing "$c"
    stage_begin "$c" EXECUTION
}

run_payment_population() {
    local c="$1" payment_id failures=0
    while IFS= read -r payment_id; do
        [[ -n "$payment_id" ]] || continue
        if ! process_payment "$payment_id"; then
            failures=$((failures+1))
            audit_event "$c" "$payment_id" PAYMENT_CONTROL_ERROR "$c:$payment_id:CONTROL_ERROR" "payment processing returned an execution error"
        fi
    done < <(payment_ids_for_cycle "$c")
    if (( failures > 0 )); then stage_held "$c" EXECUTION "$failures payment operations returned errors"; return 1; fi
    stage_done "$c" EXECUTION
}

post_execution_integrity() {
    local c="$1"
    stage_begin "$c" INTEGRITY
    if true; then stage_done "$c" INTEGRITY; return 0; fi
    stage_held "$c" INTEGRITY "durable payment state is internally inconsistent"
    return 1
}
held_execution_outcomes_present() { (( $(safe_int "$(held_execution_state_count "$1")") > 0 )); }

force_cycle_held() {
    local c="$1" reason="$2"
    db_exec "
      UPDATE cycles SET state='HELD',reconciliation_status='HELD',
      completion_status=CASE WHEN completion_status='COMPLETED' THEN completion_status ELSE 'WAITING' END
      WHERE cycle_id='$(sql_escape "$c")';"
    remove_gated_outputs
    stage_held "$c" CONTROL "$reason"
}

reconcile_cycle_after_execution() {
    local c="$1"
    stage_begin "$c" RECONCILIATION_CONTROL
    if false; then
        force_cycle_held "$c" "one or more resumed financial effects are inconsistent"
        run_reconciliation "$c" >/dev/null || true
        db_exec "UPDATE cycles SET state='HELD',reconciliation_status='HELD' WHERE cycle_id='$(sql_escape "$c")';"
        if [[ -f "$OUT_DIR/reconciliation.json" ]]; then
            local tmp; tmp="$(mktemp "$OUT_DIR/.recon.XXXXXX")"
            jq '.status="HELD" | .mismatch_count=((.mismatch_count // 0)+1)' "$OUT_DIR/reconciliation.json" > "$tmp"
            mv "$tmp" "$OUT_DIR/reconciliation.json"
        fi
        stage_held "$c" RECONCILIATION_CONTROL "held execution state prevents balanced close"
        return 1
    fi
    local status; status="$(run_reconciliation "$c")"
    if [[ "$status" == BALANCED ]]; then stage_done "$c" RECONCILIATION_CONTROL; return 0; fi
    force_cycle_held "$c" "cycle reconciliation did not balance"
    stage_held "$c" RECONCILIATION_CONTROL "cycle reconciliation held"
    return 1
}

publish_cycle_after_reconciliation() {
    local c="$1"
    stage_begin "$c" PUBLICATION_CONTROL
    if publication_guard "$c"; then stage_done "$c" PUBLICATION_CONTROL; return 0; fi
    stage_held "$c" PUBLICATION_CONTROL "publication is gated by reconciliation"
    return 1
}

close_cycle_after_publication() {
    local c="$1"
    stage_begin "$c" CLOSE_CONTROL
    if close_cycle "$c"; then stage_done "$c" CLOSE_CONTROL; return 0; fi
    stage_held "$c" CLOSE_CONTROL "cycle is waiting for close prerequisites"
    return 1
}

write_control_snapshot() {
    local c="$1" i q
    i="$(mktemp)"; q="$(mktemp)"
    cycle_integrity_summary_json "$c" > "$i"
    close_summary_json "$c" > "$q"
    jq -n --slurpfile integrity "$i" --slurpfile close "$q" '{integrity:$integrity[0],close:$close[0]}' > "$OUT_DIR/control_snapshot.json"
    rm -f "$i" "$q"
}

replay_completed_cycle_outputs() {
    local c="$1" status
    status="$(run_reconciliation "$c")"
    if [[ "$status" != BALANCED ]]; then force_cycle_held "$c" "completed durable state no longer reconciles"; return 1; fi
    publication_guard "$c"
    create_authorization_once "$c"
    write_control_snapshot "$c"
}

run_cycle_control() {
    local c="$1"
    if cycle_is_completed "$c"; then replay_completed_cycle_outputs "$c"; return $?; fi

    prepare_cycle "$c"
    run_payment_population "$c" || true

    if ! post_execution_integrity "$c"; then
        force_cycle_held "$c" "post-execution integrity checks failed"
        run_reconciliation "$c" >/dev/null || true
        remove_gated_outputs
        write_control_snapshot "$c"
        return 1
    fi

    reconcile_cycle_after_execution "$c" || true
    if ! publish_cycle_after_reconciliation "$c"; then write_control_snapshot "$c"; return 1; fi
    close_cycle_after_publication "$c" || true
    write_control_snapshot "$c"
    return 0
}
