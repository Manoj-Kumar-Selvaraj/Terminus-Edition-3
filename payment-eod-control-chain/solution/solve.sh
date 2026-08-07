#!/bin/bash
set -euo pipefail

cp /solution/correct/paydup.cob /app/eod/cobol/paydup.cob
cp /solution/correct/payexec.cob /app/eod/cobol/payexec.cob
cp /solution/correct/schema.sql /app/eod/sql/schema.sql
cp /solution/correct/run_eod.sh /app/eod/bin/run_eod.sh
chmod +x /app/eod/bin/run_eod.sh

# Rebuild the supplied sample state against the corrected integrity constraints.
rm -f /app/eod/state/payment_eod.db
mkdir -p /app/eod/state
sqlite3 /app/eod/state/payment_eod.db < /app/eod/sql/schema.sql
sqlite3 /app/eod/state/payment_eod.db < /app/eod/sql/seed.sql
/app/eod/bin/run_eod.sh
