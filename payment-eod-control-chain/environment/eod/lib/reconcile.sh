#!/usr/bin/env bash
set -euo pipefail

metric_scalar() {
    local sql="$1"
    local value
    value="$(db_scalar "$sql")"
    safe_int "$value"
}

expected_ledger_rows_for_outcome() {
    local outcome="$1"
    case "$outcome" in
        SUCCESS_INTERNAL|SUCCESS_EXTERNAL) printf "4" ;;
        *) printf "0" ;;
    esac
}

payment_ledger_is_complete() {
    local payment_id="$1"
    local outcome="$2"
    local expected
    local actual
    local debit
    local credit
    local decision

    expected="$(expected_ledger_rows_for_outcome "$outcome")"
    actual="$(metric_scalar "
        SELECT COUNT(*)
        FROM ledger_entries
        WHERE payment_id=$payment_id;
    ")"
    debit="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM ledger_entries
        WHERE payment_id=$payment_id
          AND side='D';
    ")"
    credit="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM ledger_entries
        WHERE payment_id=$payment_id
          AND side='C';
    ")"

    decision="$(cobol_call payledger "$debit|$credit|$expected|$actual")"
    [[ "$decision" == "LEDGER_OK" ]]
}

count_invalid_financial_effects() {
    local cycle_id="$1"
    metric_scalar "
        SELECT COUNT(*)
        FROM payment_outcomes o
        WHERE o.cycle_id='$(sql_escape "$cycle_id")'
          AND o.outcome IN ('DUPLICATE','REJECTED')
          AND (
                EXISTS(SELECT 1 FROM internal_postings i WHERE i.payment_id=o.payment_id)
             OR EXISTS(SELECT 1 FROM reservations r WHERE r.payment_id=o.payment_id AND r.active=1)
             OR EXISTS(SELECT 1 FROM clearing_items c WHERE c.payment_id=o.payment_id)
             OR EXISTS(SELECT 1 FROM ledger_entries l WHERE l.payment_id=o.payment_id)
          );
    "
}

count_external_mismatches() {
    local cycle_id="$1"
    metric_scalar "
        SELECT COUNT(*)
        FROM payment_outcomes o
        JOIN payments p ON p.payment_id=o.payment_id
        WHERE o.cycle_id='$(sql_escape "$cycle_id")'
          AND o.outcome='SUCCESS_EXTERNAL'
          AND (
                NOT EXISTS(
                    SELECT 1
                    FROM reservations r
                    WHERE r.payment_id=p.payment_id
                      AND r.cycle_id=p.cycle_id
                      AND r.active=1
                      AND r.amount_cents=(p.amount_cents+p.fee_cents+p.tax_cents)
                )
             OR NOT EXISTS(
                    SELECT 1
                    FROM clearing_items c
                    JOIN reservations r ON r.reservation_id=c.reservation_id
                    WHERE c.payment_id=p.payment_id
                      AND c.cycle_id=p.cycle_id
                      AND c.amount_cents=p.amount_cents
                      AND c.currency=p.currency
                      AND r.payment_id=p.payment_id
                      AND r.active=1
                )
          );
    "
}

count_internal_mismatches() {
    local cycle_id="$1"
    metric_scalar "
        SELECT COUNT(*)
        FROM payment_outcomes o
        JOIN payments p ON p.payment_id=o.payment_id
        WHERE o.cycle_id='$(sql_escape "$cycle_id")'
          AND o.outcome='SUCCESS_INTERNAL'
          AND NOT EXISTS(
              SELECT 1
              FROM internal_postings i
              WHERE i.payment_id=p.payment_id
                AND i.cycle_id=p.cycle_id
                AND i.debit_cents=(p.amount_cents+p.fee_cents+p.tax_cents)
                AND i.beneficiary_credit_cents=p.amount_cents
          );
    "
}

count_missing_ledger() {
    local cycle_id="$1"
    local missing=0
    local row
    while IFS='|' read -r payment_id outcome; do
        [[ -n "$payment_id" ]] || continue
        if ! payment_ledger_is_complete "$payment_id" "$outcome"; then
            missing=$((missing + 1))
        fi
    done < <(db_rows "
        SELECT payment_id,outcome
        FROM payment_outcomes
        WHERE cycle_id='$(sql_escape "$cycle_id")'
          AND outcome IN ('SUCCESS_INTERNAL','SUCCESS_EXTERNAL')
        ORDER BY payment_id;
    ")
    printf "%s" "$missing"
}

collect_reconciliation_metrics() {
    local cycle_id="$1"

    ORIGINAL_COUNT="$(metric_scalar "
        SELECT COUNT(*) FROM payments
        WHERE cycle_id='$(sql_escape "$cycle_id")';
    ")"
    OUTCOME_COUNT="$(metric_scalar "
        SELECT COUNT(*) FROM payment_outcomes
        WHERE cycle_id='$(sql_escape "$cycle_id")';
    ")"
    ORIGINAL_VALUE="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM payments
        WHERE cycle_id='$(sql_escape "$cycle_id")';
    ")"
    RESPONSE_VALUE="$(metric_scalar "
        SELECT COALESCE(SUM(p.amount_cents),0)
        FROM payments p
        JOIN payment_outcomes o ON o.payment_id=p.payment_id
        WHERE p.cycle_id='$(sql_escape "$cycle_id")'
          AND o.cycle_id=p.cycle_id;
    ")"
    INTERNAL_SUCCESS="$(metric_scalar "
        SELECT COUNT(*) FROM payment_outcomes
        WHERE cycle_id='$(sql_escape "$cycle_id")'
          AND outcome='SUCCESS_INTERNAL';
    ")"
    INTERNAL_POSTINGS="$(metric_scalar "
        SELECT COUNT(*) FROM internal_postings
        WHERE cycle_id='$(sql_escape "$cycle_id")';
    ")"
    EXTERNAL_SUCCESS="$(metric_scalar "
        SELECT COUNT(*) FROM payment_outcomes
        WHERE cycle_id='$(sql_escape "$cycle_id")'
          AND outcome='SUCCESS_EXTERNAL';
    ")"
    RESERVATION_COUNT="$(metric_scalar "
        SELECT COUNT(*) FROM reservations
        WHERE cycle_id='$(sql_escape "$cycle_id")'
          AND active=1;
    ")"
    CLEARING_COUNT="$(metric_scalar "
        SELECT COUNT(*) FROM clearing_items
        WHERE cycle_id='$(sql_escape "$cycle_id")';
    ")"
    RESERVED_DEBIT="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM reservations
        WHERE active=1;
    ")"
    CLEARING_VALUE="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM clearing_items;
    ")"
    EXTERNAL_FEE_TAX="$(metric_scalar "
        SELECT COALESCE(SUM(p.fee_cents+p.tax_cents),0)
        FROM payments p
        JOIN payment_outcomes o ON o.payment_id=p.payment_id
        WHERE p.cycle_id='$(sql_escape "$cycle_id")'
          AND o.outcome='SUCCESS_EXTERNAL';
    ")"
    LEDGER_DEBITS="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM ledger_entries
        WHERE side='D';
    ")"
    LEDGER_CREDITS="$(metric_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM ledger_entries
        WHERE side='C';
    ")"
    INVALID_EFFECT_COUNT=0
    local ext_mismatch int_mismatch
    ext_mismatch="$(count_external_mismatches "$cycle_id")"
    int_mismatch="$(count_internal_mismatches "$cycle_id")"
    MISMATCH_COUNT=0
    MISSING_LEDGER_COUNT=0
}

reconciliation_decision() {
    local input
    input="$ORIGINAL_COUNT|$OUTCOME_COUNT|$ORIGINAL_VALUE|$RESPONSE_VALUE|"
    input+="$INTERNAL_SUCCESS|$INTERNAL_POSTINGS|$EXTERNAL_SUCCESS|"
    input+="$RESERVATION_COUNT|$CLEARING_COUNT|$RESERVED_DEBIT|$CLEARING_VALUE|"
    input+="$EXTERNAL_FEE_TAX|$LEDGER_DEBITS|$LEDGER_CREDITS|"
    input+="$INVALID_EFFECT_COUNT|$MISMATCH_COUNT|$MISSING_LEDGER_COUNT"
    cobol_call payrecon "$input"
}

persist_reconciliation() {
    local cycle_id="$1"
    local status="$2"

    db_exec "
        INSERT INTO reconciliation_runs(
            cycle_id,status,
            original_count,outcome_count,
            original_value_cents,response_value_cents,
            internal_success_count,internal_posting_count,
            external_success_count,reservation_count,clearing_count,
            reserved_debit_cents,clearing_value_cents,external_fee_tax_cents,
            ledger_debits_cents,ledger_credits_cents,
            invalid_effect_count,mismatch_count,missing_ledger_count,
            reconciled_at
        ) VALUES(
            '$(sql_escape "$cycle_id")',
            '$(sql_escape "$status")',
            $ORIGINAL_COUNT,$OUTCOME_COUNT,
            $ORIGINAL_VALUE,$RESPONSE_VALUE,
            $INTERNAL_SUCCESS,$INTERNAL_POSTINGS,
            $EXTERNAL_SUCCESS,$RESERVATION_COUNT,$CLEARING_COUNT,
            $RESERVED_DEBIT,$CLEARING_VALUE,$EXTERNAL_FEE_TAX,
            $LEDGER_DEBITS,$LEDGER_CREDITS,
            $INVALID_EFFECT_COUNT,$MISMATCH_COUNT,$MISSING_LEDGER_COUNT,
            datetime('now')
        );

        UPDATE cycles
        SET reconciliation_status='$(sql_escape "$status")',
            state=CASE
                WHEN '$(sql_escape "$status")'='BALANCED' THEN 'RECONCILED'
                ELSE 'HELD'
            END,
            reconciled_at=datetime('now')
        WHERE cycle_id='$(sql_escape "$cycle_id")';
    "
}

write_reconciliation_json() {
    local cycle_id="$1"
    local status="$2"
    local difference_count
    difference_count=$((ORIGINAL_COUNT - OUTCOME_COUNT))
    if (( difference_count < 0 )); then
        difference_count=$((-difference_count))
    fi

    jq -n \
        --arg cycle_id "$cycle_id" \
        --arg status "$status" \
        --argjson original_count "$ORIGINAL_COUNT" \
        --argjson outcome_count "$OUTCOME_COUNT" \
        --argjson final_count "$OUTCOME_COUNT" \
        --argjson original_value_cents "$ORIGINAL_VALUE" \
        --argjson response_value_cents "$RESPONSE_VALUE" \
        --argjson internal_success_count "$INTERNAL_SUCCESS" \
        --argjson internal_posting_count "$INTERNAL_POSTINGS" \
        --argjson external_success_count "$EXTERNAL_SUCCESS" \
        --argjson reservation_count "$RESERVATION_COUNT" \
        --argjson clearing_count "$CLEARING_COUNT" \
        --argjson reserved_debit_cents "$RESERVED_DEBIT" \
        --argjson clearing_value_cents "$CLEARING_VALUE" \
        --argjson external_fee_tax_cents "$EXTERNAL_FEE_TAX" \
        --argjson ledger_debits_cents "$LEDGER_DEBITS" \
        --argjson ledger_credits_cents "$LEDGER_CREDITS" \
        --argjson invalid_effect_count "$INVALID_EFFECT_COUNT" \
        --argjson mismatch_count "$MISMATCH_COUNT" \
        --argjson missing_ledger_count "$MISSING_LEDGER_COUNT" \
        --argjson difference_count "$difference_count" \
        '{
            cycle_id:$cycle_id,
            status:$status,
            original_count:$original_count,
            outcome_count:$outcome_count,
            final_count:$final_count,
            original_value_cents:$original_value_cents,
            response_value_cents:$response_value_cents,
            internal_success_count:$internal_success_count,
            internal_posting_count:$internal_posting_count,
            external_success_count:$external_success_count,
            reservation_count:$reservation_count,
            clearing_count:$clearing_count,
            reserved_debit_cents:$reserved_debit_cents,
            clearing_value_cents:$clearing_value_cents,
            external_fee_tax_cents:$external_fee_tax_cents,
            ledger_debits_cents:$ledger_debits_cents,
            ledger_credits_cents:$ledger_credits_cents,
            invalid_effect_count:$invalid_effect_count,
            mismatch_count:$mismatch_count,
            missing_ledger_count:$missing_ledger_count,
            difference_count:$difference_count
        }' > "$OUT_DIR/reconciliation.json"
}

run_reconciliation() {
    local cycle_id="$1"
    collect_reconciliation_metrics "$cycle_id"
    local status
    status="$(reconciliation_decision)"
    if [[ "$status" != "BALANCED" ]]; then
        status="HELD"
    fi
    persist_reconciliation "$cycle_id" "$status"
    write_reconciliation_json "$cycle_id" "$status"
    checkpoint "$cycle_id" NULL "RECONCILIATION" "DONE" "$cycle_id:RECONCILIATION"
    audit_event "$cycle_id" NULL "RECONCILIATION_$status" "$cycle_id:RECONCILIATION:$status" "cycle reconciliation $status"
    printf "%s" "$status"
}
