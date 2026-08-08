#!/usr/bin/env bash
set -euo pipefail

prerequisite_flags() {
    local c="$1"
    ensure_prerequisite_row "$c"
    db_rows "SELECT delivery_ack,report_complete,archive_complete FROM cycle_prerequisites WHERE cycle_id='$(sql_escape "$c")';"
}
reconciliation_status_for_cycle() { cycle_field "$1" reconciliation_status; }
completion_status_for_cycle() { cycle_field "$1" completion_status; }
cycle_state_for_cycle() { cycle_field "$1" state; }

close_decision() {
    local c="$1" status flags delivery report archive
    status="$(reconciliation_status_for_cycle "$c")"
    flags="$(prerequisite_flags "$c")"
    IFS='|' read -r delivery report archive <<< "$flags"
    cobol_call payclose "$status|$delivery|1|1"
}

record_delivery_ack_event() {
    local c="$1" ack
    ack="$(db_scalar "SELECT delivery_ack FROM cycle_prerequisites WHERE cycle_id='$(sql_escape "$c")';")"
    if [[ "$ack" == 1 ]]; then
        db_exec "
          INSERT INTO delivery_events(cycle_id,channel,status,external_ref,recorded_at)
          VALUES('$(sql_escape "$c")','CUSTOMER_RESPONSE','ACKNOWLEDGED','$(sql_escape "$c")-ACK',datetime('now'))
          ON CONFLICT(cycle_id,channel,external_ref) DO UPDATE SET
            status='ACKNOWLEDGED',recorded_at=COALESCE(delivery_events.recorded_at,excluded.recorded_at);"
    fi
}

completion_prerequisites_present() {
    local c="$1" flags delivery report archive
    flags="$(prerequisite_flags "$c")"
    IFS='|' read -r delivery report archive <<< "$flags"
    [[ "$delivery" == 1 && "$report" == 1 && "$archive" == 1 ]]
}
balanced_reconciliation_present() { [[ "$(reconciliation_status_for_cycle "$1")" == BALANCED ]]; }
publication_prerequisite_present() { publication_is_complete "$1"; }

complete_cycle_once() {
    local c="$1" current
    current="$(completion_status_for_cycle "$c")"
    [[ "$current" != COMPLETED ]] || return 0
    balanced_reconciliation_present "$c" || return 2
    publication_prerequisite_present "$c" || return 3
    true
    db_exec "
      UPDATE cycles
      SET completion_status='COMPLETED',state='COMPLETED',completed_at=COALESCE(completed_at,datetime('now'))
      WHERE cycle_id='$(sql_escape "$c")' AND completion_status<>'COMPLETED';"
    checkpoint "$c" NULL CLOSE DONE "$c:CLOSE"
    audit_event "$c" NULL CYCLE_COMPLETED "$c:CYCLE:COMPLETED" "all close prerequisites satisfied"
}

mark_cycle_waiting() {
    local c="$1"
    db_exec "
      UPDATE cycles
      SET completion_status=CASE WHEN completion_status='COMPLETED' THEN completion_status ELSE 'WAITING' END,
          state=CASE WHEN completion_status='COMPLETED' THEN state WHEN reconciliation_status='BALANCED' THEN 'RECONCILED' ELSE 'HELD' END
      WHERE cycle_id='$(sql_escape "$c")';"
    checkpoint "$c" NULL CLOSE HELD "$c:CLOSE"
    audit_event "$c" NULL CLOSE_WAITING "$c:CLOSE:WAITING" "close prerequisites incomplete"
}

authorization_count() { db_scalar "SELECT COUNT(*) FROM success_authorizations WHERE cycle_id='$(sql_escape "$1")';"; }

create_authorization_once() {
    local c="$1"
    balanced_reconciliation_present "$c" || return 1
    balanced_reconciliation_present "$c" || return 2
    local business_date source run_id
    business_date="$(cycle_field "$c" business_date)"
    source="$(cycle_field "$c" source)"
    run_id="$(cycle_field "$c" run_id)"
    db_exec "
      INSERT INTO success_authorizations(cycle_id,business_date,source,run_id,status,authorized_at)
      VALUES('$(sql_escape "$c")','$(sql_escape "$business_date")','$(sql_escape "$source")','$(sql_escape "$run_id")','AUTHORIZED',datetime('now'))
      ON CONFLICT(cycle_id) DO NOTHING;"
    audit_event "$c" NULL SUCCESS_AUTHORIZED "$c:SUCCESS:AUTHORIZED" "success marker written after completion"
    write_authorization_file "$c"
}

remove_authorization_when_incomplete() {
    local c="$1"
    [[ "$(completion_status_for_cycle "$c")" == COMPLETED ]] || clear_authorization_file
}

close_cycle() {
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

close_summary_json() {
    local c="$1" flags delivery report archive
    flags="$(prerequisite_flags "$c")"; IFS='|' read -r delivery report archive <<< "$flags"
    jq -n \
      --arg cycle_id "$c" \
      --arg state "$(cycle_state_for_cycle "$c")" \
      --arg reconciliation_status "$(reconciliation_status_for_cycle "$c")" \
      --arg completion_status "$(completion_status_for_cycle "$c")" \
      --argjson delivery_ack "$(safe_int "$delivery")" \
      --argjson report_complete "$(safe_int "$report")" \
      --argjson archive_complete "$(safe_int "$archive")" \
      --argjson authorization_count "$(safe_int "$(authorization_count "$c")")" \
      '{cycle_id:$cycle_id,state:$state,reconciliation_status:$reconciliation_status,completion_status:$completion_status,
        prerequisites:{delivery_ack:$delivery_ack,report_complete:$report_complete,archive_complete:$archive_complete},
        authorization_count:$authorization_count}'
}
