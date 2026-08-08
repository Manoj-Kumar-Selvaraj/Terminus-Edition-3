#!/usr/bin/env bash
set -euo pipefail

checkpoint_count_for_stage() {
    local c="$1" stage="$2" status="$3"
    db_scalar "SELECT COUNT(*) FROM work_checkpoints WHERE cycle_id='$(sql_escape "$c")' AND stage='$(sql_escape "$stage")' AND status='$(sql_escape "$status")';"
}
checkpoint_count_for_payment_stage() {
    local payment_id="$1" stage="$2" status="$3"
    db_scalar "SELECT COUNT(*) FROM work_checkpoints WHERE payment_id=$payment_id AND stage='$(sql_escape "$stage")' AND status='$(sql_escape "$status")';"
}
audit_count_for_type() {
    local c="$1" event_type="$2"
    db_scalar "SELECT COUNT(*) FROM audit_events WHERE cycle_id='$(sql_escape "$c")' AND event_type='$(sql_escape "$event_type")';"
}
audit_count_for_payment_type() {
    local payment_id="$1" event_type="$2"
    db_scalar "SELECT COUNT(*) FROM audit_events WHERE payment_id=$payment_id AND event_type='$(sql_escape "$event_type")';"
}

payment_checkpoint_terminal() {
    local payment_id="$1"
    [[ "$(checkpoint_count_for_payment_stage "$payment_id" PAYMENT DONE)" == 1 ]]
}
payment_has_one_decision() {
    local payment_id="$1"
    [[ "$(db_scalar "SELECT COUNT(*) FROM payment_outcomes WHERE payment_id=$payment_id;")" == 1 ]]
}
payment_history_terminal_status() {
    local payment_id="$1" source_ref
    source_ref="$(db_scalar "SELECT source_ref FROM payments WHERE payment_id=$payment_id;")"
    db_scalar "SELECT COALESCE(status,'') FROM payment_history WHERE source_ref='$(sql_escape "$source_ref")' LIMIT 1;"
}

successful_payment_audit_present() {
    local payment_id="$1" outcome
    outcome="$(db_scalar "SELECT COALESCE(outcome,'') FROM payment_outcomes WHERE payment_id=$payment_id;")"
    case "$outcome" in
      SUCCESS_INTERNAL)
        (( $(safe_int "$(audit_count_for_payment_type "$payment_id" INTERNAL_POSTED)") + $(safe_int "$(audit_count_for_payment_type "$payment_id" INTERNAL_RESUMED)") >= 1 ))
        ;;
      SUCCESS_EXTERNAL)
        (( $(safe_int "$(audit_count_for_payment_type "$payment_id" RESERVATION_CREATED)") + $(safe_int "$(audit_count_for_payment_type "$payment_id" EXTERNAL_RESUMED)") >= 1 ))
        ;;
      DUPLICATE)
        [[ "$(audit_count_for_payment_type "$payment_id" DUPLICATE_SUPPRESSED)" == 1 ]]
        ;;
      REJECTED)
        [[ "$(audit_count_for_payment_type "$payment_id" PAYMENT_REJECTED)" == 1 ]]
        ;;
      *) return 1 ;;
    esac
}

payment_lifecycle_valid() {
    local payment_id="$1"
    payment_checkpoint_terminal "$payment_id" || return 1
    payment_has_one_decision "$payment_id" || return 2
    successful_payment_audit_present "$payment_id" || return 3
    return 0
}

cycle_payment_lifecycle_failure_count() {
    local c="$1" payment_id failures=0
    while IFS= read -r payment_id; do
        [[ -n "$payment_id" ]] || continue
        payment_lifecycle_valid "$payment_id" || failures=$((failures+1))
    done < <(payment_ids_for_cycle "$c")
    printf '%s' "$failures"
}

execution_stage_terminal() {
    local c="$1"
    local done held
    done="$(checkpoint_count_for_stage "$c" EXECUTION DONE)"
    held="$(checkpoint_count_for_stage "$c" EXECUTION HELD)"
    (( $(safe_int "$done") + $(safe_int "$held") >= 1 ))
}
integrity_stage_terminal() {
    local c="$1"
    local done held
    done="$(checkpoint_count_for_stage "$c" INTEGRITY DONE)"
    held="$(checkpoint_count_for_stage "$c" INTEGRITY HELD)"
    (( $(safe_int "$done") + $(safe_int "$held") >= 1 ))
}
reconciliation_stage_terminal() {
    local c="$1"
    local done held
    done="$(checkpoint_count_for_stage "$c" RECONCILIATION_CONTROL DONE)"
    held="$(checkpoint_count_for_stage "$c" RECONCILIATION_CONTROL HELD)"
    (( $(safe_int "$done") + $(safe_int "$held") >= 1 ))
}
publication_stage_consistent() {
    local c="$1" status
    status="$(reconciliation_status_for_cycle "$c")"
    if [[ "$status" == BALANCED ]]; then
        (( $(safe_int "$(checkpoint_count_for_stage "$c" PUBLICATION_CONTROL DONE)") >= 1 ))
    else
        (( $(safe_int "$(checkpoint_count_for_stage "$c" PUBLICATION HELD)") + $(safe_int "$(checkpoint_count_for_stage "$c" PUBLICATION_CONTROL HELD)") >= 1 ))
    fi
}
close_stage_consistent() {
    local c="$1" completion
    completion="$(completion_status_for_cycle "$c")"
    if [[ "$completion" == COMPLETED ]]; then
        (( $(safe_int "$(checkpoint_count_for_stage "$c" CLOSE DONE)") + $(safe_int "$(checkpoint_count_for_stage "$c" CLOSE_CONTROL DONE)") >= 1 ))
    else
        (( $(safe_int "$(checkpoint_count_for_stage "$c" CLOSE HELD)") + $(safe_int "$(checkpoint_count_for_stage "$c" CLOSE_CONTROL HELD)") >= 1 ))
    fi
}

completion_audit_consistent() {
    local c="$1" completion auth
    completion="$(completion_status_for_cycle "$c")"
    auth="$(authorization_count "$c")"
    if [[ "$completion" == COMPLETED ]]; then
        [[ "$(audit_count_for_type "$c" CYCLE_COMPLETED)" == 1 ]] || return 1
        [[ "$(audit_count_for_type "$c" SUCCESS_AUTHORIZED)" == 1 ]] || return 1
        [[ "$auth" == 1 ]]
    else
        [[ "$auth" == 0 ]]
    fi
}

publication_audit_consistent() {
    local c="$1" status
    status="$(reconciliation_status_for_cycle "$c")"
    if [[ "$status" == BALANCED ]]; then
        (( $(safe_int "$(audit_count_for_type "$c" PUBLICATION_COMPLETE)") >= 1 ))
    else
        (( $(safe_int "$(audit_count_for_type "$c" PUBLICATION_HELD)") >= 1 ))
    fi
}

lifecycle_failure_count() {
    local c="$1" failures=0
    (( $(safe_int "$(cycle_payment_lifecycle_failure_count "$c")") == 0 )) || failures=$((failures+1))
    execution_stage_terminal "$c" || failures=$((failures+1))
    integrity_stage_terminal "$c" || failures=$((failures+1))
    reconciliation_stage_terminal "$c" || failures=$((failures+1))
    publication_stage_consistent "$c" || failures=$((failures+1))
    close_stage_consistent "$c" || failures=$((failures+1))
    printf '%s' "$failures"
}

lifecycle_is_valid() { (( $(safe_int "$(lifecycle_failure_count "$1")") == 0 )); }

lifecycle_summary_json() {
    local c="$1"
    jq -n \
      --arg cycle_id "$c" \
      --argjson payment_lifecycle_failures "$(safe_int "$(cycle_payment_lifecycle_failure_count "$c")")" \
      --argjson lifecycle_failures "$(safe_int "$(lifecycle_failure_count "$c")")" \
      --argjson control_started "$(safe_int "$(checkpoint_count_for_stage "$c" CONTROL STARTED)")" \
      --argjson execution_done "$(safe_int "$(checkpoint_count_for_stage "$c" EXECUTION DONE)")" \
      --argjson execution_held "$(safe_int "$(checkpoint_count_for_stage "$c" EXECUTION HELD)")" \
      --argjson integrity_done "$(safe_int "$(checkpoint_count_for_stage "$c" INTEGRITY DONE)")" \
      --argjson integrity_held "$(safe_int "$(checkpoint_count_for_stage "$c" INTEGRITY HELD)")" \
      --argjson reconciliation_done "$(safe_int "$(checkpoint_count_for_stage "$c" RECONCILIATION_CONTROL DONE)")" \
      --argjson reconciliation_held "$(safe_int "$(checkpoint_count_for_stage "$c" RECONCILIATION_CONTROL HELD)")" \
      --argjson publication_done "$(safe_int "$(checkpoint_count_for_stage "$c" PUBLICATION_CONTROL DONE)")" \
      --argjson publication_held "$(safe_int "$(checkpoint_count_for_stage "$c" PUBLICATION_CONTROL HELD)")" \
      --argjson close_done "$(safe_int "$(checkpoint_count_for_stage "$c" CLOSE_CONTROL DONE)")" \
      --argjson close_held "$(safe_int "$(checkpoint_count_for_stage "$c" CLOSE_CONTROL HELD)")" \
      '{cycle_id:$cycle_id,payment_lifecycle_failures:$payment_lifecycle_failures,lifecycle_failures:$lifecycle_failures,
        control_started:$control_started,execution:{done:$execution_done,held:$execution_held},
        integrity:{done:$integrity_done,held:$integrity_held},reconciliation:{done:$reconciliation_done,held:$reconciliation_held},
        publication:{done:$publication_done,held:$publication_held},close:{done:$close_done,held:$close_held}}'
}
