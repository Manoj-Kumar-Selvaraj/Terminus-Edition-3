# EOD restart and interface notes

The database contains one already-authorized and priced payment cycle. Capture, customer validation, sanctions/risk and pricing are upstream. The batch here owns duplicate control, financial execution, reconciliation, publication and close. It can be invoked again after part of that work has already committed; persisted rows are authoritative.

## Payment identity and decision records

A `source_ref` already present in `payment_history` with status `ACCEPTED` or `COMPLETED` is a replay. A `PENDING` history row is not an accepted replay. Matching payer, beneficiary, amount, currency or purpose does not make a new source reference a duplicate.

`PAYDUP` uses pipe-delimited files with no header:

- `/app/eod/work/history.psv`: `source_ref|payer_account|beneficiary_ref|amount_cents|currency|purpose|status`
- `/app/eod/work/dup_input.psv`: `payment_id|source_ref|payer_account|beneficiary_ref|amount_cents|currency|purpose`
- `/app/eod/work/dup_output.psv`: `payment_id|UNIQUE|reason` or `payment_id|DUPLICATE|reason`

The runner must give `PAYDUP` accepted/completed history only.

`PAYEXEC` also uses pipe-delimited files with no header:

- `/app/eod/work/exec_input.psv`: `payment_id|route|payer_status|beneficiary_status|available_cents|amount_cents|fee_cents|tax_cents|existing_effect`
- `/app/eod/work/exec_output.psv`: `payment_id|action|total_debit_cents|amount_cents|fee_cents|tax_cents|reason`

`route` is `I` for a payment with `beneficiary_account` and `E` otherwise. `existing_effect` is `NONE`, `INTERNAL` or `EXTERNAL`. Actions are `POST_INTERNAL`, `RESERVE_EXTERNAL`, `ALREADY_INTERNAL`, `ALREADY_EXTERNAL` or `REJECT`.

## Financial state

The approved debit is `amount_cents + fee_cents + tax_cents`. A new effect requires an `ACTIVE` payer and, for an internal payment, an `ACTIVE` beneficiary. Available payer capacity is the current account balance less active external reservations for that payer. Insufficient capacity rejects the payment without a successful effect.

An existing internal posting or active external reservation for the same payment is already authoritative. It is resumed as success and is not posted/reserved or written to the ledger again.

A new internal success is one transaction: debit the payer by the approved debit, credit the beneficiary by the payment amount, and record the fee/tax obligations. A new external success creates one active reservation for the approved debit and one clearing item for the payment amount. Clearing is valid only for an externally successful payment that has an active reservation. A duplicate or rejected payment has no successful posting, active reservation, clearing item or ledger obligation.

Ledger obligations for an internal success are:

- debit `CUSTOMER_CONTROL` by the approved debit;
- credit `BENEFICIARY_CONTROL` by `amount_cents`;
- credit `FEE_INCOME` by `fee_cents` when non-zero;
- credit `TAX_PAYABLE` by `tax_cents` when non-zero.

For an external success use debit `CUSTOMER_RESERVED`, credit `CLEARING_PAYABLE`, plus the same fee/tax credits. Zero-value fee/tax rows may be omitted.

## Reconciliation and close

A cycle is `BALANCED` only when all of the following are true:

- every original payment has one final response outcome;
- original instructed value equals the instructed value represented by the final outcomes;
- each internal success has one internal posting;
- each external success has one active reservation and one clearing item;
- external reserved debit equals clearing value plus external fee and tax;
- ledger debits equal ledger credits and each success has the required ledger obligation;
- duplicate/rejected payments have no successful financial effect.

Otherwise reconciliation is `HELD`.

`/app/eod/out/reconciliation.json` is always written as one JSON object with exactly these fields:

`cycle_id`, `status`, `original_count`, `final_count`, `original_value_cents`, `response_value_cents`, `internal_success_count`, `internal_posting_count`, `external_success_count`, `reservation_count`, `clearing_count`, `reserved_debit_cents`, `clearing_value_cents`, `external_fee_tax_cents`, `ledger_debits_cents`, `ledger_credits_cents`, `difference_count`.

All count/value fields are integers; `status` is `BALANCED` or `HELD`.

Only a balanced cycle publishes these CSVs:

- `/app/eod/out/customer_response.csv` header: `payment_id,source_ref,outcome,reason`
- `/app/eod/out/clearing_submission.csv` header: `payment_id,source_ref,amount_cents,currency`

The clearing file contains externally successful payments with an active reservation only.

Cycle completion is `COMPLETED` only when reconciliation is balanced and `cycle_prerequisites` has `delivery_ack=1`, `report_complete=1`, and `archive_complete=1`. Otherwise completion is `HELD`.

Only a completed cycle may have `/app/eod/out/success_authorization.json`, with exactly these JSON fields: `cycle_id`, `business_date`, `source`, `run_id`, `status`. `status` is `AUTHORIZED`. There may be only one current authorization for a cycle. A held invocation must not leave the two publication CSVs when reconciliation is held, or an authorization JSON when completion is held.
