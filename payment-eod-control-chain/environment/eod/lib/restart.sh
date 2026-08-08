#!/usr/bin/env bash
set -euo pipefail

payment_durable_state() {
    local payment_id="$1"
    local posting reservation clearing ledger outcome checkpoint
    posting="$(db_scalar "SELECT COUNT(*) FROM internal_postings WHERE payment_id=$payment_id;")"
    reservation="$(db_scalar "SELECT COUNT(*) FROM reservations WHERE payment_id=$payment_id AND active=1;")"
    clearing="$(db_scalar "SELECT COUNT(*) FROM clearing_items WHERE payment_id=$payment_id;")"
    ledger="$(db_scalar "SELECT COUNT(*) FROM ledger_entries WHERE payment_id=$payment_id;")"
    outcome="$(db_scalar "SELECT COALESCE(outcome,'') FROM payment_outcomes WHERE payment_id=$payment_id;")"
    checkpoint="$(db_scalar "SELECT COUNT(*) FROM work_checkpoints WHERE payment_id=$payment_id AND stage='PAYMENT' AND status='DONE';")"
    printf '%s|%s|%s|%s|%s|%s' "$posting" "$reservation" "$clearing" "$ledger" "$outcome" "$checkpoint"
}

payment_route_kind() {
    local payment_id="$1"
    local beneficiary
    beneficiary="$(db_scalar "SELECT COALESCE(beneficiary_account,'') FROM payments WHERE payment_id=$payment_id;")"
    [[ -n "$beneficiary" ]] && printf INTERNAL || printf EXTERNAL
}

payment_expected_total_debit() {
    local payment_id="$1" row amount fee tax
    row="$(db_rows "SELECT amount_cents,fee_cents,tax_cents FROM payments WHERE payment_id=$payment_id;")"
    IFS='|' read -r amount fee tax <<< "$row"
    total_debit_for_payment "$amount" "$fee" "$tax"
}

payment_has_conflicting_effect_families() {
    local payment_id="$1"
    local posting reservation
    posting="$(db_scalar "SELECT COUNT(*) FROM internal_postings WHERE payment_id=$payment_id;")"
    reservation="$(db_scalar "SELECT COUNT(*) FROM reservations WHERE payment_id=$payment_id AND active=1;")"
    (( $(safe_int "$posting") > 0 && $(safe_int "$reservation") > 0 ))
}

internal_posting_consistent() {
    local payment_id="$1" row expected debit credit amount
    row="$(db_rows "SELECT p.amount_cents,i.debit_cents,i.beneficiary_credit_cents FROM payments p JOIN internal_postings i ON i.payment_id=p.payment_id WHERE p.payment_id=$payment_id LIMIT 1;")"
    [[ -n "$row" ]] || return 1
    IFS='|' read -r amount debit credit <<< "$row"
    expected="$(payment_expected_total_debit "$payment_id")"
    [[ "$debit" == "$expected" && "$credit" == "$amount" ]]
}

external_reservation_consistent() {
    local payment_id="$1" expected amount
    expected="$(payment_expected_total_debit "$payment_id")"
    amount="$(db_scalar "SELECT COALESCE(amount_cents,-1) FROM reservations WHERE payment_id=$payment_id AND active=1 ORDER BY reservation_id LIMIT 1;")"
    [[ "$amount" == "$expected" ]]
}

external_clearing_consistent() {
    local payment_id="$1" row payment_amount payment_currency clear_amount clear_currency
    row="$(db_rows "SELECT p.amount_cents,p.currency,x.amount_cents,x.currency FROM payments p JOIN clearing_items x ON x.payment_id=p.payment_id WHERE p.payment_id=$payment_id LIMIT 1;")"
    [[ -n "$row" ]] || return 1
    IFS='|' read -r payment_amount payment_currency clear_amount clear_currency <<< "$row"
    [[ "$payment_amount" == "$clear_amount" && "$payment_currency" == "$clear_currency" ]]
}

payment_restart_class() {
    local payment_id="$1" kind state posting reservation clearing ledger outcome checkpoint
    kind="$(payment_route_kind "$payment_id")"
    state="$(payment_durable_state "$payment_id")"
    IFS='|' read -r posting reservation clearing ledger outcome checkpoint <<< "$state"

    if [[ "$kind" == INTERNAL ]]; then
        if (( $(safe_int "$posting") > 0 )); then
            if internal_posting_consistent "$payment_id"; then printf RESUME_INTERNAL; else printf INCONSISTENT_INTERNAL; fi
        else
            printf NEW_INTERNAL
        fi
        return
    fi

    if (( $(safe_int "$reservation") > 0 )); then
        printf RESUME_EXTERNAL
    elif (( $(safe_int "$clearing") > 0 )); then
        printf CLEARING_WITHOUT_RESERVATION
    else
        printf NEW_EXTERNAL
    fi
}

restart_state_is_safe_to_enter() {
    local payment_id="$1" class
    class="$(payment_restart_class "$payment_id")"
    case "$class" in
        NEW_INTERNAL|NEW_EXTERNAL|RESUME_INTERNAL|RESUME_EXTERNAL) return 0 ;;
        *) return 1 ;;
    esac
}

record_restart_observation() {
    local cycle_id="$1" payment_id="$2" class="$3"
    audit_event "$cycle_id" "$payment_id" RESTART_OBSERVED "$cycle_id:$payment_id:RESTART_OBSERVED" "$class"
}

scan_restart_state() {
    local cycle_id="$1" payment_id class unsafe=0
    while IFS= read -r payment_id; do
        [[ -n "$payment_id" ]] || continue
        class="$(payment_restart_class "$payment_id")"
        record_restart_observation "$cycle_id" "$payment_id" "$class"
        case "$class" in
            CONFLICTING_EFFECTS|INCONSISTENT_INTERNAL|INCONSISTENT_EXTERNAL|CLEARING_WITHOUT_RESERVATION)
                unsafe=$((unsafe+1))
                ;;
        esac
    done < <(payment_ids_for_cycle "$cycle_id")
    printf '%s' "$unsafe"
}

restart_class_count() {
    local cycle_id="$1" wanted="$2" payment_id class count=0
    while IFS= read -r payment_id; do
        [[ -n "$payment_id" ]] || continue
        class="$(payment_restart_class "$payment_id")"
        [[ "$class" == "$wanted" ]] && count=$((count+1))
    done < <(payment_ids_for_cycle "$cycle_id")
    printf '%s' "$count"
}

write_restart_report() {
    local cycle_id="$1" tmp first=1 payment_id class state
    tmp="$(mktemp "$OUT_DIR/.restart.XXXXXX")"
    printf '{"cycle_id":"%s","payments":[' "$(printf '%s' "$cycle_id" | sed 's/"/\\"/g')" > "$tmp"
    while IFS= read -r payment_id; do
        [[ -n "$payment_id" ]] || continue
        class="$(payment_restart_class "$payment_id")"
        state="$(payment_durable_state "$payment_id")"
        local posting reservation clearing ledger outcome checkpoint
        IFS='|' read -r posting reservation clearing ledger outcome checkpoint <<< "$state"
        (( first == 1 )) || printf ',' >> "$tmp"
        first=0
        jq -cn \
          --argjson payment_id "$payment_id" --arg class "$class" \
          --argjson posting_count "$(safe_int "$posting")" \
          --argjson active_reservation_count "$(safe_int "$reservation")" \
          --argjson clearing_count "$(safe_int "$clearing")" \
          --argjson ledger_count "$(safe_int "$ledger")" \
          --arg outcome "$outcome" --argjson checkpoint_count "$(safe_int "$checkpoint")" \
          '{payment_id:$payment_id,class:$class,posting_count:$posting_count,active_reservation_count:$active_reservation_count,clearing_count:$clearing_count,ledger_count:$ledger_count,outcome:$outcome,checkpoint_count:$checkpoint_count}' >> "$tmp"
    done < <(payment_ids_for_cycle "$cycle_id")
    printf ']}' >> "$tmp"
    jq . "$tmp" > "$OUT_DIR/restart_report.json"
    rm -f "$tmp"
}

restart_report_safe_count() {
    local cycle_id="$1"
    local total unsafe
    total="$(cycle_payment_count "$cycle_id")"
    unsafe="$(scan_restart_state "$cycle_id")"
    printf '%s' "$(( $(safe_int "$total") - $(safe_int "$unsafe") ))"
}
