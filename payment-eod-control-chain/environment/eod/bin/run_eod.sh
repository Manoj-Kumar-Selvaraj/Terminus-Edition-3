#!/bin/bash
set -euo pipefail
ROOT=/app/eod
DB="$ROOT/state/payment_eod.db"
WORK="$ROOT/work"
OUT="$ROOT/out"
mkdir -p "$WORK" "$OUT"
rm -f "$WORK"/* "$OUT"/*

cobc -x -free -o "$WORK/paydup" "$ROOT/cobol/paydup.cob"
cobc -x -free -o "$WORK/payexec" "$ROOT/cobol/payexec.cob"

sqlite3 -separator '|' -noheader "$DB" "SELECT source_ref,payer_account,beneficiary_ref,amount_cents,currency,purpose,status FROM payment_history WHERE status IN ('ACCEPTED','COMPLETED');" > "$WORK/history.psv"
sqlite3 -separator '|' -noheader "$DB" "SELECT payment_id,source_ref,payer_account,beneficiary_ref,amount_cents,currency,purpose FROM payments ORDER BY payment_id;" > "$WORK/dup_input.psv"
"$WORK/paydup"

while IFS='|' read -r pid outcome reason; do
  if [ "$outcome" = "DUPLICATE" ]; then
    sqlite3 "$DB" "INSERT OR REPLACE INTO payment_outcomes(payment_id,outcome,reason) VALUES($pid,'DUPLICATE','$reason');"
  else
    sqlite3 "$DB" "INSERT OR REPLACE INTO payment_outcomes(payment_id,outcome,reason) VALUES($pid,'ELIGIBLE','DUPLICATE_CLEAR');"
  fi
done < "$WORK/dup_output.psv"

sqlite3 -separator '|' -noheader "$DB" "
SELECT p.payment_id,
       CASE WHEN p.beneficiary_account IS NULL THEN 'E' ELSE 'I' END,
       pa.status,
       COALESCE(ba.status,'NA'),
       pa.balance_cents - COALESCE((SELECT SUM(r.amount_cents) FROM reservations r WHERE r.payment_id IN (SELECT payment_id FROM payments x WHERE x.payer_account=p.payer_account) AND r.active=1),0),
       p.amount_cents,p.fee_cents,p.tax_cents,
       CASE WHEN EXISTS(SELECT 1 FROM internal_postings i WHERE i.payment_id=p.payment_id) THEN 'INTERNAL'
            WHEN EXISTS(SELECT 1 FROM reservations r WHERE r.payment_id=p.payment_id AND r.active=1) THEN 'EXTERNAL'
            ELSE 'NONE' END
FROM payments p
JOIN payment_outcomes o ON o.payment_id=p.payment_id AND o.outcome='ELIGIBLE'
JOIN accounts pa ON pa.account_id=p.payer_account
LEFT JOIN accounts ba ON ba.account_id=p.beneficiary_account
ORDER BY p.payment_id;" > "$WORK/exec_input.psv"
"$WORK/payexec"

while IFS='|' read -r pid action total amount fee tax reason; do
  payer=$(sqlite3 "$DB" "SELECT payer_account FROM payments WHERE payment_id=$pid;")
  beneficiary=$(sqlite3 "$DB" "SELECT COALESCE(beneficiary_account,'') FROM payments WHERE payment_id=$pid;")
  case "$action" in
    *INTERNAL)
      sqlite3 "$DB" "BEGIN; INSERT INTO internal_postings(payment_id,debit_cents,beneficiary_credit_cents) VALUES($pid,$total,$amount); UPDATE accounts SET balance_cents=balance_cents-$total WHERE account_id='$payer'; UPDATE accounts SET balance_cents=balance_cents+$amount WHERE account_id='$beneficiary'; INSERT INTO ledger_entries(payment_id,side,account_code,amount_cents) VALUES($pid,'D','CUSTOMER_CONTROL',$total),($pid,'C','BENEFICIARY_CONTROL',$amount),($pid,'C','FEE_INCOME',$fee),($pid,'C','TAX_PAYABLE',$tax); INSERT OR REPLACE INTO payment_outcomes(payment_id,outcome,reason) VALUES($pid,'SUCCESS_INTERNAL','POSTED'); COMMIT;"
      ;;
    *EXTERNAL)
      sqlite3 "$DB" "BEGIN; INSERT INTO reservations(payment_id,amount_cents,active) VALUES($pid,$total,1); INSERT INTO ledger_entries(payment_id,side,account_code,amount_cents) VALUES($pid,'D','CUSTOMER_RESERVED',$total),($pid,'C','CLEARING_PAYABLE',$amount),($pid,'C','FEE_INCOME',$fee),($pid,'C','TAX_PAYABLE',$tax); INSERT OR REPLACE INTO payment_outcomes(payment_id,outcome,reason) VALUES($pid,'SUCCESS_EXTERNAL','RESERVED'); COMMIT;"
      ;;
    *)
      sqlite3 "$DB" "INSERT OR REPLACE INTO payment_outcomes(payment_id,outcome,reason) VALUES($pid,'REJECTED','$reason');"
      ;;
  esac
done < "$WORK/exec_output.psv"

sqlite3 "$DB" "INSERT INTO clearing_items(payment_id,amount_cents,currency) SELECT p.payment_id,p.amount_cents,p.currency FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id WHERE p.beneficiary_account IS NULL AND o.outcome='SUCCESS_EXTERNAL';"

cycle_id=$(sqlite3 "$DB" "SELECT cycle_id FROM cycles LIMIT 1;")
business_date=$(sqlite3 "$DB" "SELECT business_date FROM cycles WHERE cycle_id='$cycle_id';")
source=$(sqlite3 "$DB" "SELECT source FROM cycles WHERE cycle_id='$cycle_id';")
run_id=$(sqlite3 "$DB" "SELECT run_id FROM cycles WHERE cycle_id='$cycle_id';")
original_count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM payments WHERE cycle_id='$cycle_id';")
final_count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM payment_outcomes o JOIN payments p ON p.payment_id=o.payment_id WHERE p.cycle_id='$cycle_id';")
original_value=$(sqlite3 "$DB" "SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE cycle_id='$cycle_id';")
response_value=$(sqlite3 "$DB" "SELECT COALESCE(SUM(p.amount_cents),0) FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id WHERE p.cycle_id='$cycle_id';")
internal_success=$(sqlite3 "$DB" "SELECT COUNT(*) FROM payment_outcomes WHERE outcome='SUCCESS_INTERNAL';")
internal_postings=$(sqlite3 "$DB" "SELECT COUNT(*) FROM internal_postings;")
external_success=$(sqlite3 "$DB" "SELECT COUNT(*) FROM payment_outcomes WHERE outcome='SUCCESS_EXTERNAL';")
reservation_count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM reservations WHERE active=1;")
clearing_count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM clearing_items;")
reserved_debit=$(sqlite3 "$DB" "SELECT COALESCE(SUM(amount_cents),0) FROM reservations WHERE active=1;")
clearing_value=$(sqlite3 "$DB" "SELECT COALESCE(SUM(amount_cents),0) FROM clearing_items;")
ext_fee_tax=$(sqlite3 "$DB" "SELECT COALESCE(SUM(p.fee_cents+p.tax_cents),0) FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id WHERE o.outcome='SUCCESS_EXTERNAL';")
ledger_debits=$(sqlite3 "$DB" "SELECT COALESCE(SUM(amount_cents),0) FROM ledger_entries WHERE side='D';")
ledger_credits=$(sqlite3 "$DB" "SELECT COALESCE(SUM(amount_cents),0) FROM ledger_entries WHERE side='C';")
differences=0
[ "$original_count" = "$final_count" ] || differences=$((differences+1))
[ "$original_value" = "$response_value" ] || differences=$((differences+1))
[ "$internal_success" = "$internal_postings" ] || differences=$((differences+1))
[ "$external_success" = "$reservation_count" ] || differences=$((differences+1))
[ "$external_success" = "$clearing_count" ] || differences=$((differences+1))
[ "$reserved_debit" = $((clearing_value+ext_fee_tax)) ] || differences=$((differences+1))
[ "$ledger_debits" = "$ledger_credits" ] || differences=$((differences+1))
status=BALANCED
[ "$differences" -eq 0 ] || status=HELD

cat > "$OUT/reconciliation.json" <<EOF
{"cycle_id":"$cycle_id","status":"$status","original_count":$original_count,"final_count":$final_count,"original_value_cents":$original_value,"response_value_cents":$response_value,"internal_success_count":$internal_success,"internal_posting_count":$internal_postings,"external_success_count":$external_success,"reservation_count":$reservation_count,"clearing_count":$clearing_count,"reserved_debit_cents":$reserved_debit,"clearing_value_cents":$clearing_value,"external_fee_tax_cents":$ext_fee_tax,"ledger_debits_cents":$ledger_debits,"ledger_credits_cents":$ledger_credits,"difference_count":$differences}
EOF
echo 'payment_id,source_ref,outcome,reason' > "$OUT/customer_response.csv"
sqlite3 -csv -noheader "$DB" "SELECT p.payment_id,p.source_ref,o.outcome,o.reason FROM payments p JOIN payment_outcomes o ON o.payment_id=p.payment_id ORDER BY p.payment_id;" >> "$OUT/customer_response.csv"
echo 'payment_id,source_ref,amount_cents,currency' > "$OUT/clearing_submission.csv"
sqlite3 -csv -noheader "$DB" "SELECT p.payment_id,p.source_ref,c.amount_cents,c.currency FROM clearing_items c JOIN payments p ON p.payment_id=c.payment_id ORDER BY p.payment_id;" >> "$OUT/clearing_submission.csv"
sqlite3 "$DB" "INSERT OR REPLACE INTO completion_register(cycle_id,status,original_count,final_count,original_value_cents,response_value_cents) VALUES('$cycle_id','COMPLETED',$original_count,$final_count,$original_value,$response_value); UPDATE cycles SET completion_status='COMPLETED' WHERE cycle_id='$cycle_id'; INSERT OR REPLACE INTO success_authorizations(cycle_id,business_date,source,run_id,status) VALUES('$cycle_id','$business_date','$source','$run_id','AUTHORIZED');"
cat > "$OUT/success_authorization.json" <<EOF
{"cycle_id":"$cycle_id","business_date":"$business_date","source":"$source","run_id":"$run_id","status":"AUTHORIZED"}
EOF
