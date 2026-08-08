#!/usr/bin/env bash
set -euo pipefail

payer_balance() {
    local payer="$1"
    db_scalar "SELECT COALESCE(balance_cents,0) FROM accounts WHERE account_id='$(sql_escape "$payer")';"
}
payer_active_reservations() {
    local payer="$1"
    db_scalar "SELECT COALESCE(SUM(amount_cents),0) FROM reservations WHERE active=1;"
}
payer_available_capacity() {
    local payer="$1" balance reserved
    balance="$(safe_int "$(payer_balance "$payer")")"
    reserved="$(safe_int "$(payer_active_reservations "$payer")")"
    printf '%s' "$((balance-reserved))"
}
cycle_distinct_payers() {
    local c="$1"
    db_rows "SELECT DISTINCT payer_account FROM payments WHERE cycle_id='$(sql_escape "$c")' ORDER BY payer_account;"
}
cycle_requested_debit_for_payer() {
    local c="$1" payer="$2"
    db_scalar "SELECT COALESCE(SUM(amount_cents+fee_cents+tax_cents),0) FROM payments WHERE cycle_id='$(sql_escape "$c")' AND payer_account='$(sql_escape "$payer")';"
}
cycle_success_debit_for_payer() {
    local c="$1" payer="$2"
    db_scalar "
      SELECT COALESCE(SUM(p.amount_cents+p.fee_cents+p.tax_cents),0)
      FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id
      WHERE p.cycle_id='$(sql_escape "$c")' AND p.payer_account='$(sql_escape "$payer")'
        AND o.outcome IN ('SUCCESS_INTERNAL','SUCCESS_EXTERNAL');"
}
cycle_rejected_debit_for_payer() {
    local c="$1" payer="$2"
    db_scalar "
      SELECT COALESCE(SUM(p.amount_cents+p.fee_cents+p.tax_cents),0)
      FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id
      WHERE p.cycle_id='$(sql_escape "$c")' AND p.payer_account='$(sql_escape "$payer")'
        AND o.outcome='REJECTED';"
}
payer_capacity_snapshot_row() {
    local c="$1" payer="$2"
    printf '%s|%s|%s|%s|%s|%s|%s' \
      "$payer" \
      "$(safe_int "$(payer_balance "$payer")")" \
      "$(safe_int "$(payer_active_reservations "$payer")")" \
      "$(safe_int "$(payer_available_capacity "$payer")")" \
      "$(safe_int "$(cycle_requested_debit_for_payer "$c" "$payer")")" \
      "$(safe_int "$(cycle_success_debit_for_payer "$c" "$payer")")" \
      "$(safe_int "$(cycle_rejected_debit_for_payer "$c" "$payer")")"
}

write_capacity_report() {
    local c="$1" tmp payer first=1
    tmp="$(mktemp "$OUT_DIR/.capacity.XXXXXX")"
    printf '{"cycle_id":"%s","payers":[' "$(printf '%s' "$c" | sed 's/"/\\"/g')" > "$tmp"
    while IFS= read -r payer; do
        [[ -n "$payer" ]] || continue
        local row balance reserved available requested success rejected
        row="$(payer_capacity_snapshot_row "$c" "$payer")"
        IFS='|' read -r payer balance reserved available requested success rejected <<< "$row"
        (( first == 1 )) || printf ',' >> "$tmp"
        first=0
        jq -cn \
          --arg payer_account "$payer" \
          --argjson balance_cents "$balance" \
          --argjson active_reserved_cents "$reserved" \
          --argjson available_capacity_cents "$available" \
          --argjson requested_debit_cents "$requested" \
          --argjson successful_debit_cents "$success" \
          --argjson rejected_debit_cents "$rejected" \
          '{payer_account:$payer_account,balance_cents:$balance_cents,active_reserved_cents:$active_reserved_cents,
            available_capacity_cents:$available_capacity_cents,requested_debit_cents:$requested_debit_cents,
            successful_debit_cents:$successful_debit_cents,rejected_debit_cents:$rejected_debit_cents}' >> "$tmp"
    done < <(cycle_distinct_payers "$c")
    printf ']}' >> "$tmp"
    jq . "$tmp" > "$OUT_DIR/capacity_report.json"
    rm -f "$tmp"
}

payer_negative_available_count() {
    local c="$1" payer count=0 available
    while IFS= read -r payer; do
        [[ -n "$payer" ]] || continue
        available="$(payer_available_capacity "$payer")"
        (( available < 0 )) && count=$((count+1))
    done < <(cycle_distinct_payers "$c")
    printf '%s' "$count"
}
capacity_state_valid() { (( $(safe_int "$(payer_negative_available_count "$1")") == 0 )); }
