# Payment EOD business contract

The database contains one authorized, risk-permitted and priced payment population. Earlier capture, envelope, content, customer, account, sanctions and risk stages are outside this exercise. The runner owns the modeled chain from duplicate prevention through completion authorization.

## Population and duplicate control

Every original payment has exactly one final current outcome and remains visible in the customer response. An exact source reference already accepted in `payment_history` is a duplicate and must not create a financial effect. Similar payer, beneficiary and amount values are not enough to reject a new instruction; a legitimate recurring payment with a new source reference remains eligible. Reprocessing preserves prior authoritative decisions and must not create a second posting, reservation, clearing item, response result, ledger obligation, completion row or success authorization.

## COBOL decision interfaces

`/app/eod/cobol/paydup.cob` reads `/app/eod/work/history.psv` as `source_ref|payer_account|beneficiary_ref|amount_cents|currency|purpose|status`, reads `/app/eod/work/dup_input.psv` as `payment_id|source_ref|payer_account|beneficiary_ref|amount_cents|currency|purpose`, and writes `/app/eod/work/dup_output.psv` as `payment_id|UNIQUE|reason` or `payment_id|DUPLICATE|reason`. `/app/eod/cobol/payexec.cob` reads `/app/eod/work/exec_input.psv` as `payment_id|route|payer_status|beneficiary_status|available_cents|amount_cents|fee_cents|tax_cents|existing_effect` and writes `/app/eod/work/exec_output.psv` as `payment_id|action|total_debit_cents|amount_cents|fee_cents|tax_cents|reason`. Existing effects are `NONE`, `INTERNAL`, or `EXTERNAL`; the permitted actions are `POST_INTERNAL`, `RESERVE_EXTERNAL`, `ALREADY_INTERNAL`, `ALREADY_EXTERNAL`, and `REJECT`.

## Financial execution

A payment is internal when `beneficiary_account` is populated, otherwise it is external. The approved debit requirement is `amount_cents + fee_cents + tax_cents`. The payer and, for internal payments, beneficiary account must be `ACTIVE` at execution time. Available payer capacity is current balance less active external reservations. If the capacity is insufficient, the payment is rejected with no successful financial effect.

An internal success is one atomic business event: debit the payer by the approved debit requirement, credit the beneficiary by `amount_cents`, and recognize fee and tax obligations. An external success has exactly one active reservation for the approved debit requirement and exactly one clearing item for `amount_cents`. A prior authoritative internal posting or active external reservation for the same payment is resumed as success rather than executed again.

## Accounting and reconciliation

Each successful payment has balanced ledger obligations. For an internal success: debit `CUSTOMER_CONTROL` by total debit; credit `BENEFICIARY_CONTROL` by payment amount, `FEE_INCOME` by fee, and `TAX_PAYABLE` by tax. For an external success: debit `CUSTOMER_RESERVED` by total debit; credit `CLEARING_PAYABLE` by payment amount, `FEE_INCOME` by fee, and `TAX_PAYABLE` by tax. Zero-value fee or tax entries may be omitted.

Reconciliation is `BALANCED` only when all of these hold: original count equals final response count; original instructed value equals response instructed value; every internal success has one internal posting; every external success has one active reservation and one clearing item; external reserved debit equals clearing value plus external fee and tax; ledger debits equal credits; duplicate/rejected payments have no successful financial effect. Any failed equation makes the status `HELD` and blocks publication.

## Publication, completion and success

The reconciled customer response and clearing submission become official only for a `BALANCED` run. Clearing contains only externally successful, actively reserved payments. Completion is `COMPLETED` only when reconciliation is balanced and `cycle_prerequisites` records delivery acknowledgement, reporting completion and archive completion. Otherwise completion is `HELD`. Only a completed run may have one current success authorization; rerunning the same completed cycle must keep that single authorization.
