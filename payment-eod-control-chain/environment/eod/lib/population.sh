#!/usr/bin/env bash
set -euo pipefail

population_source_ref_blank_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")' AND TRIM(source_ref)='';"
}
population_payer_blank_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")' AND TRIM(payer_account)='';"
}
population_beneficiary_blank_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")' AND TRIM(beneficiary_ref)='';"
}
population_invalid_amount_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")' AND amount_cents<=0;"
}
population_invalid_charge_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")' AND (fee_cents<0 OR tax_cents<0);"
}
population_currency_blank_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")' AND TRIM(currency)='';"
}
population_purpose_blank_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")' AND TRIM(purpose)='';"
}
population_duplicate_source_within_cycle_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM (SELECT source_ref FROM payments WHERE cycle_id='$(sql_escape "$c")' GROUP BY source_ref HAVING COUNT(*)>1);"
}
population_duplicate_sequence_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM (SELECT received_seq FROM payments WHERE cycle_id='$(sql_escape "$c")' GROUP BY received_seq HAVING COUNT(*)>1);"
}
population_missing_payer_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments p LEFT JOIN accounts a ON a.account_id=p.payer_account WHERE p.cycle_id='$(sql_escape "$c")' AND a.account_id IS NULL;"
}
population_missing_internal_beneficiary_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments p LEFT JOIN accounts a ON a.account_id=p.beneficiary_account WHERE p.cycle_id='$(sql_escape "$c")' AND p.beneficiary_account IS NOT NULL AND a.account_id IS NULL;"
}
population_external_with_account_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payments WHERE cycle_id='$(sql_escape "$c")' AND beneficiary_account IS NOT NULL AND beneficiary_ref<>beneficiary_account;"
}
population_source_history_conflict_count() {
    local c="$1"
    db_scalar "
      SELECT COUNT(*) FROM payments p JOIN payment_history h ON h.source_ref=p.source_ref
      WHERE p.cycle_id='$(sql_escape "$c")' AND h.status IN ('ACCEPTED','COMPLETED')
        AND COALESCE(h.accepted_cycle_id,'') NOT IN ('',p.cycle_id);"
}
population_commercial_similarity_count() {
    local c="$1"
    db_scalar "
      SELECT COUNT(*) FROM payments p
      WHERE p.cycle_id='$(sql_escape "$c")'
        AND EXISTS(
          SELECT 1 FROM payment_history h
          WHERE h.source_ref<>p.source_ref AND h.payer_account=p.payer_account
            AND h.beneficiary_ref=p.beneficiary_ref AND h.amount_cents=p.amount_cents
            AND h.currency=p.currency AND h.purpose=p.purpose
            AND h.status IN ('ACCEPTED','COMPLETED')
        );"
}
population_current_cycle_history_count() {
    local c="$1"
    db_scalar "SELECT COUNT(*) FROM payment_history WHERE accepted_cycle_id='$(sql_escape "$c")';"
}

population_validation_failures() {
    local c="$1" failures=0 value
    for value in \
      "$(population_source_ref_blank_count "$c")" \
      "$(population_payer_blank_count "$c")" \
      "$(population_beneficiary_blank_count "$c")" \
      "$(population_invalid_amount_count "$c")" \
      "$(population_invalid_charge_count "$c")" \
      "$(population_currency_blank_count "$c")" \
      "$(population_purpose_blank_count "$c")" \
      "$(population_duplicate_source_within_cycle_count "$c")" \
      "$(population_duplicate_sequence_count "$c")" \
      "$(population_missing_payer_count "$c")" \
      "$(population_missing_internal_beneficiary_count "$c")"
    do
        (( $(safe_int "$value") == 0 )) || failures=$((failures+1))
    done
    printf '%s' "$failures"
}

population_is_valid() { (( $(safe_int "$(population_validation_failures "$1")") == 0 )); }

population_summary_json() {
    local c="$1"
    jq -n \
      --arg cycle_id "$c" \
      --argjson payment_count "$(safe_int "$(cycle_payment_count "$c")")" \
      --argjson source_history_conflicts "$(safe_int "$(population_source_history_conflict_count "$c")")" \
      --argjson commercial_similarity "$(safe_int "$(population_commercial_similarity_count "$c")")" \
      --argjson current_cycle_history "$(safe_int "$(population_current_cycle_history_count "$c")")" \
      --argjson validation_failures "$(safe_int "$(population_validation_failures "$c")")" \
      '{cycle_id:$cycle_id,payment_count:$payment_count,source_history_conflicts:$source_history_conflicts,
        commercial_similarity:$commercial_similarity,current_cycle_history:$current_cycle_history,
        validation_failures:$validation_failures}'
}
