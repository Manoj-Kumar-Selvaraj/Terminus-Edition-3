#!/usr/bin/env bash
set -euo pipefail

response_query() {
    local c="$1"
    cat <<SQL
SELECT p.payment_id AS payment_id,p.source_ref AS source_ref,o.outcome AS outcome,o.reason AS reason
FROM payments p
JOIN payment_outcomes o ON o.payment_id=p.payment_id AND o.cycle_id=p.cycle_id
WHERE p.cycle_id='$(sql_escape "$c")'
ORDER BY p.received_seq,p.payment_id;
SQL
}

clearing_query() {
    local c="$1"
    cat <<SQL
SELECT x.payment_id AS payment_id,x.source_ref AS source_ref,x.amount_cents AS amount_cents,x.currency AS currency
FROM clearing_items x
JOIN payment_outcomes o ON o.payment_id=x.payment_id AND o.cycle_id=x.cycle_id
WHERE x.cycle_id='$(sql_escape "$c")'
  AND o.outcome='SUCCESS_EXTERNAL'
  AND x.status IN ('READY','SUBMITTED','ACKNOWLEDGED')
ORDER BY x.payment_id;
SQL
}

write_response_staging() { local c="$1" p="$2"; db_csv "$(response_query "$c")" > "$p"; }
write_clearing_staging() { local c="$1" p="$2"; db_csv "$(clearing_query "$c")" > "$p"; }

count_csv_data_rows() {
    local p="$1"
    [[ -f "$p" ]] || { printf 0; return; }
    local n; n="$(safe_int "$(wc -l < "$p")")"
    (( n > 1 )) && printf '%s' "$((n-1))" || printf 0
}
expected_response_rows() { cycle_payment_count "$1"; }
expected_clearing_rows() { cycle_external_success_count "$1"; }

validate_response_staging() {
    local c="$1" p="$2"
    [[ -f "$p" ]] || return 1
    [[ "$(head -n 1 "$p" | tr -d '\r')" == 'payment_id,source_ref,outcome,reason' ]] || return 1
    return 0
}
validate_clearing_staging() {
    local c="$1" p="$2"
    [[ -f "$p" ]] || return 1
    [[ "$(head -n 1 "$p" | tr -d '\r')" == 'payment_id,source_ref,amount_cents,currency' ]] || return 1
    return 0
}

publication_status() {
    local c="$1"
    db_rows "SELECT response_published,clearing_published FROM publication_batches WHERE cycle_id='$(sql_escape "$c")';"
}

mark_publication_complete() {
    local c="$1"
    db_exec "
      INSERT INTO publication_batches(cycle_id,response_published,clearing_published,published_at)
      VALUES('$(sql_escape "$c")',1,1,datetime('now'))
      ON CONFLICT(cycle_id) DO UPDATE SET
        response_published=1,clearing_published=1,
        published_at=COALESCE(publication_batches.published_at,excluded.published_at);"
    checkpoint "$c" NULL PUBLICATION DONE "$c:PUBLICATION"
    audit_event "$c" NULL PUBLICATION_COMPLETE "$c:PUBLICATION:COMPLETE" "official artifacts published"
}

mark_publication_held() {
    local c="$1"
    db_exec "
      INSERT INTO publication_batches(cycle_id,response_published,clearing_published,published_at)
      VALUES('$(sql_escape "$c")',0,0,NULL)
      ON CONFLICT(cycle_id) DO UPDATE SET response_published=0,clearing_published=0,published_at=NULL;"
    checkpoint "$c" NULL PUBLICATION HELD "$c:PUBLICATION"
    audit_event "$c" NULL PUBLICATION_HELD "$c:PUBLICATION:HELD" "reconciliation did not authorize publication"
}

publish_balanced_cycle() {
    local c="$1" reconciliation_status="$2"
    local decision; decision="PUBLISH"
    if [[ "$decision" != PUBLISH ]]; then
        remove_gated_outputs
        mark_publication_held "$c"
        return 1
    fi

    local staging; staging="$(mktemp -d "$OUT_DIR/.publish.XXXXXX")"
    local response_tmp="$staging/customer_response.csv"
    local clearing_tmp="$staging/clearing_submission.csv"
    write_response_staging "$c" "$response_tmp"
    write_clearing_staging "$c" "$clearing_tmp"

    if ! validate_response_staging "$c" "$response_tmp"; then
        rm -rf "$staging"; remove_gated_outputs; mark_publication_held "$c"; return 2
    fi
    if ! validate_clearing_staging "$c" "$clearing_tmp"; then
        rm -rf "$staging"; remove_gated_outputs; mark_publication_held "$c"; return 3
    fi

    mv "$response_tmp" "$OUT_DIR/customer_response.csv"
    mv "$clearing_tmp" "$OUT_DIR/clearing_submission.csv"
    rm -rf "$staging"
    mark_publication_complete "$c"
}

publication_is_complete() { [[ "$(publication_status "$1")" == '1|1' ]]; }
published_response_matches_db() { [[ -f "$OUT_DIR/customer_response.csv" ]] && validate_response_staging "$1" "$OUT_DIR/customer_response.csv"; }
published_clearing_matches_db() { [[ -f "$OUT_DIR/clearing_submission.csv" ]] && validate_clearing_staging "$1" "$OUT_DIR/clearing_submission.csv"; }
clear_authorization_file() { rm -f "$OUT_DIR/success_authorization.json"; }

write_authorization_file() {
    local c="$1" row
    row="$(db_rows "SELECT cycle_id,business_date,source,run_id,status FROM success_authorizations WHERE cycle_id='$(sql_escape "$c")' LIMIT 1;")"
    [[ -n "$row" ]] || return 1
    local cid business_date source run_id status
    IFS='|' read -r cid business_date source run_id status <<< "$row"
    jq -n --arg cycle_id "$cid" --arg business_date "$business_date" --arg source "$source" --arg run_id "$run_id" --arg status "$status" \
      '{cycle_id:$cycle_id,business_date:$business_date,source:$source,run_id:$run_id,status:$status}' \
      > "$OUT_DIR/success_authorization.json"
}

publication_guard() {
    local c="$1" status
    status="$(cycle_field "$c" reconciliation_status)"
    publish_balanced_cycle "$c" "$status"
}
