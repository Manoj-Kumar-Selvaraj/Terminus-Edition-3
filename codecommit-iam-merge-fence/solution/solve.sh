#!/usr/bin/env bash
set -euo pipefail

ROOT="${CC_ROOT:-/app/codecommit}"
LIB="${ROOT}/lib/cc"

cp /solution/fixed/iam.py "${LIB}/iam.py"
cp /solution/fixed/gitops.py "${LIB}/gitops.py"
cp /solution/fixed/prs.py "${LIB}/prs.py"
cp /solution/fixed/trigger.py "${LIB}/trigger.py"

mkdir -p "${ROOT}/var/repos"
if [[ ! -f "${ROOT}/var/repos/ledger.git/HEAD" ]]; then
  PYTHONPATH="${ROOT}/lib" python3 "${ROOT}/lib/cc/seed.py"
fi
