#!/usr/bin/env bash
set -euo pipefail

ROOT="${CC_ROOT:-/app/codecommit}"
LIB="${ROOT}/lib/cc"
SRC="/solution/fixed"

cp "${SRC}/actions.py" "${LIB}/iam/actions.py"
cp "${SRC}/conditions.py" "${LIB}/iam/conditions.py"
cp "${SRC}/eval.py" "${LIB}/iam/eval.py"
cp "${SRC}/approvals.py" "${LIB}/prs/approvals.py"
cp "${SRC}/merge.py" "${LIB}/prs/merge.py"
cp "${SRC}/deliver.py" "${LIB}/pipelines/deliver.py"
cp "${SRC}/event_id.py" "${LIB}/pipelines/event_id.py"
cp "${SRC}/log.py" "${LIB}/audit/log.py"
cp "${SRC}/retry.py" "${LIB}/webhooks/retry.py"
cp "${SRC}/app.py" "${LIB}/api/app.py"
cp "${SRC}/authz_gateway.py" "${LIB}/services/authz_gateway.py"
cp "${SRC}/cli.py" "${LIB}/cli.py"
cp "${SRC}/gitops.py" "${LIB}/repos/gitops.py"

mkdir -p "${ROOT}/var/repos"
if [[ ! -f "${ROOT}/var/repos/ledger.git/HEAD" ]]; then
  PYTHONPATH="${ROOT}/lib" python3 "${ROOT}/lib/cc/seed.py"
fi
