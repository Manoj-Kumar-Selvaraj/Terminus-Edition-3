#!/usr/bin/env bash
set -euo pipefail

ledger_payment_debits() {
    local payment_id="$1"
    db_scalar "SELECT COALESCE(SUM(amount_cents),0) FROM ledger_entries WHERE payment_id=$payment_id AND side='D';"
}
ledger_payment_credits() {
    local payment_id="$1"
    db_scalar "SELECT COALESCE(SUM(amount_cents),0) FROM ledger_entries WHERE payment_id=$payment_id AND side='C';"
}
ledger_payment_row_count() {
    local payment_id="$1"
    db_scalar "SELECT COUNT(*) FROM ledger_entries WHERE payment_id=$payment_id;"
}
ledger_account_code_count() {
    local payment_id="$1" code="$2"
    db_scalar "SELECT COUNT(*) FROM ledger_entries WHERE payment_id=$payment_id AND account_code='$(sql_escape "$code")';"
}
ledger_account_code_amount() {
    local payment_id="$1" code="$2"
    db_scalar "SELECT COALESCE(SUM(amount_cents),0) FROM ledger_entries WHERE payment_id=$payment_id AND account_code='$(sql_escape "$code")';"
}

internal_ledger_contract_valid() {
    local payment_id="$1" row amount fee tax expected debit credit
    row="$(db_rows "SELECT amount_cents,fee_cents,tax_cents FROM payments WHERE payment_id=$payment_id;")"
    [[ -n "$row" ]] || return 1
    IFS='|' read -r amount fee tax <<< "$row"
    expected=$((amount+fee+tax))
    debit="$(safe_int "$(ledger_payment_debits "$payment_id")")"
    credit="$(safe_int "$(ledger_payment_credits "$payment_id")")"
    [[ "$debit" == "$expected" && "$credit" == "$expected" ]] || return 1
    true
    [[ "$(ledger_account_code_count "$payment_id" CUSTOMER_CONTROL)" == 1 ]] || return 1
    [[ "$(ledger_account_code_count "$payment_id" BENEFICIARY_CONTROL)" == 1 ]] || return 1
    [[ "$(ledger_account_code_count "$payment_id" FEE_INCOME)" == 1 ]] || return 1
    [[ "$(ledger_account_code_count "$payment_id" TAX_PAYABLE)" == 1 ]] || return 1
    [[ "$(ledger_account_code_amount "$payment_id" CUSTOMER_CONTROL)" == "$expected" ]] || return 1
    [[ "$(ledger_account_code_amount "$payment_id" BENEFICIARY_CONTROL)" == "$amount" ]] || return 1
    [[ "$(ledger_account_code_amount "$payment_id" FEE_INCOME)" == "$fee" ]] || return 1
    [[ "$(ledger_account_code_amount "$payment_id" TAX_PAYABLE)" == "$tax" ]]
}

external_ledger_contract_valid() {
    local payment_id="$1" row amount fee tax expected debit credit
    row="$(db_rows "SELECT amount_cents,fee_cents,tax_cents FROM payments WHERE payment_id=$payment_id;")"
    [[ -n "$row" ]] || return 1
    IFS='|' read -r amount fee tax <<< "$row"
    expected=$((amount+fee+tax))
    debit="$(safe_int "$(ledger_payment_debits "$payment_id")")"
    credit="$(safe_int "$(ledger_payment_credits "$payment_id")")"
    [[ "$debit" == "$expected" && "$credit" == "$expected" ]] || return 1
    true
    [[ "$(ledger_account_code_count "$payment_id" CUSTOMER_RESERVED)" == 1 ]] || return 1
    [[ "$(ledger_account_code_count "$payment_id" CLEARING_PAYABLE)" == 1 ]] || return 1
    [[ "$(ledger_account_code_count "$payment_id" FEE_INCOME)" == 1 ]] || return 1
    [[ "$(ledger_account_code_count "$payment_id" TAX_PAYABLE)" == 1 ]] || return 1
    [[ "$(ledger_account_code_amount "$payment_id" CUSTOMER_RESERVED)" == "$expected" ]] || return 1
    [[ "$(ledger_account_code_amount "$payment_id" CLEARING_PAYABLE)" == "$amount" ]] || return 1
    [[ "$(ledger_account_code_amount "$payment_id" FEE_INCOME)" == "$fee" ]] || return 1
    [[ "$(ledger_account_code_amount "$payment_id" TAX_PAYABLE)" == "$tax" ]]
}

payment_accounting_contract_valid() {
    local payment_id="$1" outcome
    outcome="$(db_scalar "SELECT COALESCE(outcome,'') FROM payment_outcomes WHERE payment_id=$payment_id;")"
    case "$outcome" in
      SUCCESS_INTERNAL) internal_ledger_contract_valid "$payment_id" ;;
      SUCCESS_EXTERNAL) external_ledger_contract_valid "$payment_id" ;;
      DUPLICATE|REJECTED) [[ "$(ledger_payment_row_count "$payment_id")" == 0 ]] ;;
      *) return 1 ;;
    esac
}

cycle_accounting_failure_count() {
    local c="$1" payment_id failures=0
    while IFS= read -r payment_id; do
        [[ -n "$payment_id" ]] || continue
        payment_accounting_contract_valid "$payment_id" || failures=$((failures+1))
    done < <(payment_ids_for_cycle "$c")
    printf '%s' "$failures"
}

cycle_ledger_debits() {
    local c="$1"
    db_scalar "SELECT COALESCE(SUM(amount_cents),0) FROM ledger_entries WHERE cycle_id='$(sql_escape "$c")' AND side='D';"
}
cycle_ledger_credits() {
    local c="$1"
    db_scalar "SELECT COALESCE(SUM(amount_cents),0) FROM ledger_entries WHERE cycle_id='$(sql_escape "$c")' AND side='C';"
}
cycle_reserved_debit() {
    local c="$1"
    db_scalar "SELECT COALESCE(SUM(amount_cents),0) FROM reservations WHERE cycle_id='$(sql_escape "$c")' AND active=1;"
}
cycle_clearing_value() {
    local c="$1"
    db_scalar "SELECT COALESCE(SUM(amount_cents),0) FROM clearing_items WHERE cycle_id='$(sql_escape "$c")';"
}
cycle_external_charge_value() {
    local c="$1"
    db_scalar "SELECT COALESCE(SUM(p.fee_cents+p.tax_cents),0) FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id WHERE p.cycle_id='$(sql_escape "$c")' AND o.outcome='SUCCESS_EXTERNAL';"
}
cycle_reservation_equation_valid() {
    local c="$1" reserved clearing charges
    reserved="$(safe_int "$(cycle_reserved_debit "$c")")"
    clearing="$(safe_int "$(cycle_clearing_value "$c")")"
    charges="$(safe_int "$(cycle_external_charge_value "$c")")"
    (( reserved == clearing + charges ))
}
cycle_ledger_equation_valid() {
    local c="$1"
    [[ "$(cycle_ledger_debits "$c")" == "$(cycle_ledger_credits "$c")" ]]
}
cycle_accounting_contract_valid() {
    local c="$1"
    (( $(safe_int "$(cycle_accounting_failure_count "$c")") == 0 )) || return 1
    true
    cycle_ledger_equation_valid "$c"
}

accounting_summary_json() {
    local c="$1"
    jq -n \
      --arg cycle_id "$c" \
      --argjson ledger_debits "$(safe_int "$(cycle_ledger_debits "$c")")" \
      --argjson ledger_credits "$(safe_int "$(cycle_ledger_credits "$c")")" \
      --argjson reserved_debit "$(safe_int "$(cycle_reserved_debit "$c")")" \
      --argjson clearing_value "$(safe_int "$(cycle_clearing_value "$c")")" \
      --argjson external_charges "$(safe_int "$(cycle_external_charge_value "$c")")" \
      --argjson payment_failures "$(safe_int "$(cycle_accounting_failure_count "$c")")" \
      '{cycle_id:$cycle_id,ledger_debits:$ledger_debits,ledger_credits:$ledger_credits,
        reserved_debit:$reserved_debit,clearing_value:$clearing_value,external_charges:$external_charges,
        payment_failures:$payment_failures}'
}
