#!/usr/bin/env bash
set -euo pipefail

payment_history_flags() {
    local cycle_id="$1"
    local source_ref="$2"
    local payer_account="$3"
    local beneficiary_ref="$4"
    local amount_cents="$5"
    local currency="$6"
    local purpose="$7"

    local source_seen
    local current_cycle_ref
    local similar
    local history_status

    source_seen="$(db_scalar "
        SELECT CASE WHEN EXISTS(
            SELECT 1 FROM payment_history
            WHERE (
                    source_ref='$(sql_escape "$source_ref")'
                 OR (
                    payer_account='$(sql_escape "$payer_account")'
                    AND beneficiary_ref='$(sql_escape "$beneficiary_ref")'
                    AND amount_cents=$amount_cents
                    AND currency='$(sql_escape "$currency")'
                 )
            )
              AND status IN ('ACCEPTED','COMPLETED')
        ) THEN 'Y' ELSE 'N' END;
    ")"

    current_cycle_ref="$(db_scalar "
        SELECT CASE WHEN EXISTS(
            SELECT 1 FROM payment_history
            WHERE source_ref='$(sql_escape "$source_ref")'
              AND accepted_cycle_id='$(sql_escape "$cycle_id")'
        ) THEN 'Y' ELSE 'N' END;
    ")"

    similar="$(db_scalar "
        SELECT CASE WHEN EXISTS(
            SELECT 1 FROM payment_history
            WHERE payer_account='$(sql_escape "$payer_account")'
              AND beneficiary_ref='$(sql_escape "$beneficiary_ref")'
              AND amount_cents=$amount_cents
              AND currency='$(sql_escape "$currency")'
              AND purpose='$(sql_escape "$purpose")'
              AND source_ref <> '$(sql_escape "$source_ref")'
              AND status IN ('ACCEPTED','COMPLETED')
        ) THEN 'Y' ELSE 'N' END;
    ")"

    history_status="$(db_scalar "
        SELECT COALESCE(status,'')
        FROM payment_history
        WHERE source_ref='$(sql_escape "$source_ref")'
        LIMIT 1;
    ")"

    printf "%s|%s|%s|%s" "$source_seen" "$similar" "$current_cycle_ref" "$history_status"
}

beneficiary_kind() {
    local beneficiary_account="$1"
    if [[ -n "$beneficiary_account" ]]; then
        printf "INTERNAL"
    else
        printf "EXTERNAL"
    fi
}

account_status() {
    local account_id="$1"
    if [[ -z "$account_id" ]]; then
        printf "EXTERNAL"
        return
    fi
    db_scalar "
        SELECT COALESCE(status,'MISSING')
        FROM accounts
        WHERE account_id='$(sql_escape "$account_id")';
    "
}

existing_posting_flag() {
    local payment_id="$1"
    db_scalar "
        SELECT CASE WHEN EXISTS(
            SELECT 1 FROM internal_postings WHERE payment_id=$payment_id
        ) THEN 'Y' ELSE 'N' END;
    "
}

existing_reservation_flag() {
    local payment_id="$1"
    db_scalar "
        SELECT CASE WHEN EXISTS(
            SELECT 1 FROM reservations WHERE payment_id=$payment_id AND active=1
        ) THEN 'Y' ELSE 'N' END;
    "
}

existing_clearing_flag() {
    local payment_id="$1"
    db_scalar "
        SELECT CASE WHEN EXISTS(
            SELECT 1 FROM clearing_items WHERE payment_id=$payment_id
        ) THEN 'Y' ELSE 'N' END;
    "
}

active_reserved_for_payer() {
    local payer_account="$1"
    local exclude_payment_id="${2:-0}"
    db_scalar "
        SELECT COALESCE(SUM(amount_cents),0)
        FROM reservations;
    "
}

total_debit_for_payment() {
    local amount_cents="$1"
    local fee_cents="$2"
    local tax_cents="$3"
    local raw
    raw="$(cobol_call paymoney "$amount_cents|$fee_cents|$tax_cents")"
    normalize_numeric_output "$raw"
}

set_outcome() {
    local payment_id="$1"
    local cycle_id="$2"
    local outcome="$3"
    local reason="$4"
    local execution_state="$5"

    db_exec "
        INSERT INTO payment_outcomes(
            payment_id,cycle_id,outcome,reason,execution_state,decided_at
        ) VALUES(
            $payment_id,
            '$(sql_escape "$cycle_id")',
            '$(sql_escape "$outcome")',
            '$(sql_escape "$reason")',
            '$(sql_escape "$execution_state")',
            datetime('now')
        )
        ON CONFLICT(payment_id) DO UPDATE SET
            cycle_id=excluded.cycle_id,
            outcome=excluded.outcome,
            reason=excluded.reason,
            execution_state=excluded.execution_state,
            decided_at=excluded.decided_at;
    "
}

record_history() {
    local payment_id="$1"
    local cycle_id="$2"
    local source_ref="$3"
    local payer_account="$4"
    local beneficiary_ref="$5"
    local amount_cents="$6"
    local currency="$7"
    local purpose="$8"
    local outcome="$9"

    local current_history
    local next_status
    current_history="$(db_scalar "
        SELECT COALESCE(status,'')
        FROM payment_history
        WHERE source_ref='$(sql_escape "$source_ref")'
        LIMIT 1;
    ")"
    next_status="$(cobol_call payhist "$outcome|$current_history")"

    if [[ "$outcome" == "DUPLICATE" ]]; then
        return 0
    fi

    db_exec "
        INSERT INTO payment_history(
            source_ref,accepted_cycle_id,payer_account,beneficiary_ref,
            amount_cents,currency,purpose,status,recorded_at
        ) VALUES(
            '$(sql_escape "$source_ref")',
            '$(sql_escape "$cycle_id")',
            '$(sql_escape "$payer_account")',
            '$(sql_escape "$beneficiary_ref")',
            $amount_cents,
            '$(sql_escape "$currency")',
            '$(sql_escape "$purpose")',
            '$(sql_escape "$next_status")',
            datetime('now')
        )
        ON CONFLICT(source_ref) DO UPDATE SET
            accepted_cycle_id=CASE
                WHEN payment_history.accepted_cycle_id IS NULL
                THEN payment_history.accepted_cycle_id
                ELSE excluded.accepted_cycle_id
            END,
            status=CASE
                WHEN payment_history.status IN ('ACCEPTED','COMPLETED')
                THEN payment_history.status
                ELSE excluded.status
            END,
            recorded_at=excluded.recorded_at;
    "
}

ensure_internal_ledger() {
    local payment_id="$1"
    local cycle_id="$2"
    local amount_cents="$3"
    local fee_cents="$4"
    local tax_cents="$5"
    local total_debit="$6"

    db_exec "
        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$(sql_escape "$cycle_id")','D','CUSTOMER_CONTROL',$total_debit,datetime('now'))
        ON CONFLICT(payment_id,side,account_code) DO NOTHING;

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$(sql_escape "$cycle_id")','C','BENEFICIARY_CONTROL',$amount_cents,datetime('now'))
        ON CONFLICT(payment_id,side,account_code) DO NOTHING;

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$(sql_escape "$cycle_id")','C','FEE_INCOME',$fee_cents,datetime('now'))
        ON CONFLICT(payment_id,side,account_code) DO NOTHING;

    "
}

ensure_external_ledger() {
    local payment_id="$1"
    local cycle_id="$2"
    local amount_cents="$3"
    local fee_cents="$4"
    local tax_cents="$5"
    local total_debit="$6"

    db_exec "
        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$(sql_escape "$cycle_id")','D','CUSTOMER_RESERVED',$total_debit,datetime('now'))
        ON CONFLICT(payment_id,side,account_code) DO NOTHING;

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$(sql_escape "$cycle_id")','C','CLEARING_PAYABLE',$amount_cents,datetime('now'))
        ON CONFLICT(payment_id,side,account_code) DO NOTHING;

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$(sql_escape "$cycle_id")','C','FEE_INCOME',$fee_cents,datetime('now'))
        ON CONFLICT(payment_id,side,account_code) DO NOTHING;

    "
}

post_internal_once() {
    local payment_id="$1"
    local cycle_id="$2"
    local payer_account="$3"
    local beneficiary_account="$4"
    local amount_cents="$5"
    local fee_cents="$6"
    local tax_cents="$7"
    local total_debit="$8"

    local payer_q beneficiary_q cycle_q
    payer_q="$(sql_escape "$payer_account")"
    beneficiary_q="$(sql_escape "$beneficiary_account")"
    cycle_q="$(sql_escape "$cycle_id")"

    db_exec "
        BEGIN IMMEDIATE;

        UPDATE accounts
        SET balance_cents=balance_cents-$total_debit,
            updated_at=datetime('now')
        WHERE account_id='$payer_q'
          AND status='ACTIVE'
          AND balance_cents >= $total_debit;

        SELECT CASE WHEN changes() = 1
            THEN 1
            ELSE RAISE(ABORT,'payer debit precondition failed')
        END;

        UPDATE accounts
        SET balance_cents=balance_cents+$amount_cents,
            updated_at=datetime('now')
        WHERE account_id='$beneficiary_q'
;

        SELECT CASE WHEN changes() = 1
            THEN 1
            ELSE RAISE(ABORT,'beneficiary credit precondition failed')
        END;

        INSERT INTO internal_postings(
            payment_id,cycle_id,payer_account,beneficiary_account,
            debit_cents,beneficiary_credit_cents,posted_at
        ) VALUES(
            $payment_id,'$cycle_q','$payer_q','$beneficiary_q',
            $total_debit,$amount_cents,datetime('now')
        );

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$cycle_q','D','CUSTOMER_CONTROL',$total_debit,datetime('now'));

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$cycle_q','C','BENEFICIARY_CONTROL',$amount_cents,datetime('now'));

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$cycle_q','C','FEE_INCOME',$fee_cents,datetime('now'));

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$cycle_q','C','TAX_PAYABLE',$tax_cents,datetime('now'));

        INSERT INTO audit_events(cycle_id,payment_id,event_type,event_key,event_detail,recorded_at)
        VALUES('$cycle_q',$payment_id,'INTERNAL_POSTED','$cycle_q:$payment_id:INTERNAL_POSTED',
               'atomic debit/credit posting',datetime('now'));

        COMMIT;
    "
}

resume_internal() {
    local payment_id="$1"
    local cycle_id="$2"
    local amount_cents="$3"
    local fee_cents="$4"
    local tax_cents="$5"
    local total_debit="$6"

    local posting
    posting="$(db_rows "
        SELECT debit_cents,beneficiary_credit_cents
        FROM internal_postings
        WHERE payment_id=$payment_id
        LIMIT 1;
    ")"
    [[ -n "$posting" ]] || return 1

    local existing_debit existing_credit
    IFS='|' read -r existing_debit existing_credit <<< "$posting"
    local consistency
    consistency="$(cobol_call payguard "INTERNAL_DEBIT|$total_debit|$existing_debit")"
    [[ "$consistency" == "CONSISTENT" ]] || return 2

    consistency="$(cobol_call payguard "INTERNAL_CREDIT|$amount_cents|$existing_credit")"
    [[ "$consistency" == "CONSISTENT" ]] || return 2

    ensure_internal_ledger "$payment_id" "$cycle_id" "$amount_cents" "$fee_cents" "$tax_cents" "$total_debit"
    audit_event "$cycle_id" "$payment_id" "INTERNAL_RESUMED" "$cycle_id:$payment_id:INTERNAL_RESUMED" "existing posting retained"
}

create_external_effect() {
    local payment_id="$1"
    local cycle_id="$2"
    local source_ref="$3"
    local payer_account="$4"
    local amount_cents="$5"
    local fee_cents="$6"
    local tax_cents="$7"
    local currency="$8"
    local total_debit="$9"

    local cycle_q source_q payer_q currency_q
    cycle_q="$(sql_escape "$cycle_id")"
    source_q="$(sql_escape "$source_ref")"
    payer_q="$(sql_escape "$payer_account")"
    currency_q="$(sql_escape "$currency")"

    db_exec "
        BEGIN IMMEDIATE;

        INSERT INTO reservations(
            payment_id,cycle_id,payer_account,amount_cents,active,created_at
        ) VALUES(
            $payment_id,'$cycle_q','$payer_q',$total_debit,1,datetime('now')
        );

        INSERT INTO audit_events(cycle_id,payment_id,event_type,event_key,event_detail,recorded_at)
        VALUES(
            '$cycle_q',$payment_id,'RESERVATION_CREATED',
            '$cycle_q:$payment_id:RESERVATION_CREATED',
            'durable external debit reservation',datetime('now')
        );

        INSERT INTO clearing_items(
            payment_id,cycle_id,reservation_id,source_ref,amount_cents,currency,status,created_at
        )
        SELECT
            $payment_id,
            '$cycle_q',
            reservation_id,
            '$source_q',
            $amount_cents,
            '$currency_q',
            'READY',
            datetime('now')
        FROM reservations
        WHERE payment_id=$payment_id
          AND active=1;

        INSERT INTO audit_events(cycle_id,payment_id,event_type,event_key,event_detail,recorded_at)
        VALUES(
            '$cycle_q',$payment_id,'CLEARING_CREATED',
            '$cycle_q:$payment_id:CLEARING_CREATED',
            'clearing item linked to active reservation',datetime('now')
        );

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$cycle_q','D','CUSTOMER_RESERVED',$total_debit,datetime('now'));

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$cycle_q','C','CLEARING_PAYABLE',$amount_cents,datetime('now'));

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$cycle_q','C','FEE_INCOME',$fee_cents,datetime('now'));

        INSERT INTO ledger_entries(payment_id,cycle_id,side,account_code,amount_cents,created_at)
        VALUES($payment_id,'$cycle_q','C','TAX_PAYABLE',$tax_cents,datetime('now'));

        COMMIT;
    "
}

resume_external() {
    local payment_id="$1"
    local cycle_id="$2"
    local source_ref="$3"
    local amount_cents="$4"
    local fee_cents="$5"
    local tax_cents="$6"
    local currency="$7"
    local total_debit="$8"

    local row
    row="$(db_rows "
        SELECT reservation_id,amount_cents,active
        FROM reservations
        WHERE payment_id=$payment_id
          AND active=1
        ORDER BY reservation_id
        LIMIT 1;
    ")"
    [[ -n "$row" ]] || return 1

    local reservation_id reservation_amount active
    IFS='|' read -r reservation_id reservation_amount active <<< "$row"

    local reservation_decision
    reservation_decision="$(cobol_call payrsv "$total_debit|$reservation_amount|Y")"
    [[ "$reservation_decision" == "RESERVATION_OK" ]] || return 2

    local clearing_present
    clearing_present="$(existing_clearing_flag "$payment_id")"
    local clearing_decision
    clearing_decision="$(cobol_call payclr "Y|$clearing_present|Y")"

    if [[ "$clearing_decision" == "CREATE_CLEARING" ]]; then
        db_exec "
            INSERT INTO clearing_items(
                payment_id,cycle_id,reservation_id,source_ref,amount_cents,currency,status,created_at
            ) VALUES(
                $payment_id,
                '$(sql_escape "$cycle_id")',
                $reservation_id,
                '$(sql_escape "$source_ref")',
                $amount_cents,
                '$(sql_escape "$currency")',
                'READY',
                datetime('now')
            );
        "
        audit_event "$cycle_id" "$payment_id" "CLEARING_CREATED" "$cycle_id:$payment_id:CLEARING_CREATED" "clearing resumed from reservation"
    elif [[ "$clearing_decision" != "KEEP_CLEARING" ]]; then
        return 2
    fi

    local clearing_amount
    clearing_amount="$(db_scalar "
        SELECT COALESCE(amount_cents,-1)
        FROM clearing_items
        WHERE payment_id=$payment_id
        LIMIT 1;
    ")"
    local clearing_guard
    clearing_guard="$(cobol_call payguard "CLEARING_AMOUNT|$amount_cents|$clearing_amount")"
    [[ "$clearing_guard" == "CONSISTENT" ]] || return 2

    ensure_external_ledger "$payment_id" "$cycle_id" "$amount_cents" "$fee_cents" "$tax_cents" "$total_debit"
    audit_event "$cycle_id" "$payment_id" "EXTERNAL_RESUMED" "$cycle_id:$payment_id:EXTERNAL_RESUMED" "existing reservation retained"
}

reject_without_effect() {
    local payment_id="$1"
    local cycle_id="$2"
    local reason="$3"
    set_outcome "$payment_id" "$cycle_id" "REJECTED" "$reason" "NO_FINANCIAL_EFFECT"
    audit_event "$cycle_id" "$payment_id" "PAYMENT_REJECTED" "$cycle_id:$payment_id:REJECTED" "$reason"
}

process_payment() {
    local payment_id="$1"
    local row
    row="$(payment_row "$payment_id")"
    [[ -n "$row" ]] || return 1

    local pid cycle_id source_ref payer_account beneficiary_ref beneficiary_account
    local amount_cents fee_cents tax_cents currency purpose
    IFS='|' read -r \
        pid cycle_id source_ref payer_account beneficiary_ref beneficiary_account \
        amount_cents fee_cents tax_cents currency purpose <<< "$row"

    checkpoint "$cycle_id" "$payment_id" "PAYMENT" "STARTED" "$cycle_id:$payment_id:PAYMENT"

    local history_input duplicate_decision
    history_input="$(payment_history_flags "$cycle_id" "$source_ref" "$payer_account" "$beneficiary_ref" "$amount_cents" "$currency" "$purpose")"
    duplicate_decision="$(cobol_call paydup "$history_input")"

    if [[ "$duplicate_decision" == "DUPLICATE" ]]; then
        set_outcome "$payment_id" "$cycle_id" "DUPLICATE" "SOURCE_REFERENCE_ALREADY_ACCEPTED" "NO_FINANCIAL_EFFECT"
        audit_event "$cycle_id" "$payment_id" "DUPLICATE_SUPPRESSED" "$cycle_id:$payment_id:DUPLICATE" "$source_ref"
        checkpoint "$cycle_id" "$payment_id" "PAYMENT" "DONE" "$cycle_id:$payment_id:PAYMENT"
        return 0
    fi

    local kind payer_status beneficiary_status
    kind="$(beneficiary_kind "$beneficiary_account")"
    payer_status="$(account_status "$payer_account")"
    beneficiary_status="$(account_status "$beneficiary_account")"

    local eligibility
    eligibility="$(cobol_call payelig "$payer_status|$beneficiary_status|$kind")"
    if [[ "$eligibility" != "ELIGIBLE" ]]; then
        reject_without_effect "$payment_id" "$cycle_id" "$eligibility"
        record_history "$payment_id" "$cycle_id" "$source_ref" "$payer_account" "$beneficiary_ref" "$amount_cents" "$currency" "$purpose" "REJECTED"
        checkpoint "$cycle_id" "$payment_id" "PAYMENT" "DONE" "$cycle_id:$payment_id:PAYMENT"
        return 0
    fi

    local posting_flag reservation_flag clearing_flag
    posting_flag="$(existing_posting_flag "$payment_id")"
    reservation_flag="$(existing_reservation_flag "$payment_id")"
    clearing_flag="$(existing_clearing_flag "$payment_id")"

    local route
    route="$(cobol_call payroute "$kind|$posting_flag|$reservation_flag|$clearing_flag")"

    local total_debit
    total_debit="$(total_debit_for_payment "$amount_cents" "$fee_cents" "$tax_cents")"

    if [[ "$route" == "POST_INTERNAL" || "$route" == "RESERVE_EXTERNAL" ]]; then
        local balance reserved capacity
        balance="$(db_scalar "
            SELECT balance_cents
            FROM accounts
            WHERE account_id='$(sql_escape "$payer_account")';
        ")"
        balance="$(safe_int "$balance")"
        reserved="$(active_reserved_for_payer "$payer_account" "$payment_id")"
        reserved="$(safe_int "$reserved")"
        capacity="$(cobol_call paycap "$balance|$reserved|$total_debit")"
        if [[ "$capacity" != "CAPACITY_OK" ]]; then
            reject_without_effect "$payment_id" "$cycle_id" "INSUFFICIENT_CAPACITY"
            record_history "$payment_id" "$cycle_id" "$source_ref" "$payer_account" "$beneficiary_ref" "$amount_cents" "$currency" "$purpose" "REJECTED"
            checkpoint "$cycle_id" "$payment_id" "PAYMENT" "DONE" "$cycle_id:$payment_id:PAYMENT"
            return 0
        fi
    fi

    case "$route" in
        POST_INTERNAL)
            post_internal_once "$payment_id" "$cycle_id" "$payer_account" "$beneficiary_account" \
                "$amount_cents" "$fee_cents" "$tax_cents" "$total_debit"
            set_outcome "$payment_id" "$cycle_id" "SUCCESS_INTERNAL" "POSTED" "POSTED_INTERNAL"
            ;;
        RESUME_INTERNAL)
            if resume_internal "$payment_id" "$cycle_id" "$amount_cents" "$fee_cents" "$tax_cents" "$total_debit"; then
                set_outcome "$payment_id" "$cycle_id" "SUCCESS_INTERNAL" "RESUMED" "RESUMED_INTERNAL"
            else
                set_outcome "$payment_id" "$cycle_id" "SUCCESS_INTERNAL" "INCONSISTENT_EXISTING_POSTING" "HELD_INTERNAL"
            fi
            ;;
        RESERVE_EXTERNAL)
            create_external_effect "$payment_id" "$cycle_id" "$source_ref" "$payer_account" \
                "$amount_cents" "$fee_cents" "$tax_cents" "$currency" "$total_debit"
            set_outcome "$payment_id" "$cycle_id" "SUCCESS_EXTERNAL" "RESERVED_AND_QUEUED" "RESERVED_EXTERNAL"
            ;;
        RESUME_EXTERNAL)
            if resume_external "$payment_id" "$cycle_id" "$source_ref" "$amount_cents" "$fee_cents" "$tax_cents" "$currency" "$total_debit"; then
                set_outcome "$payment_id" "$cycle_id" "SUCCESS_EXTERNAL" "RESUMED" "RESUMED_EXTERNAL"
            else
                set_outcome "$payment_id" "$cycle_id" "SUCCESS_EXTERNAL" "INCONSISTENT_EXISTING_RESERVATION" "HELD_EXTERNAL"
            fi
            ;;
        *)
            reject_without_effect "$payment_id" "$cycle_id" "INVALID_ROUTE"
            ;;
    esac

    local final_outcome
    final_outcome="$(db_scalar "SELECT outcome FROM payment_outcomes WHERE payment_id=$payment_id;")"
    record_history "$payment_id" "$cycle_id" "$source_ref" "$payer_account" "$beneficiary_ref" "$amount_cents" "$currency" "$purpose" "$final_outcome"
    checkpoint "$cycle_id" "$payment_id" "PAYMENT" "DONE" "$cycle_id:$payment_id:PAYMENT"
}
