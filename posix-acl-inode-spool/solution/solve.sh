#!/usr/bin/env bash
set -euo pipefail

ROOT="${SPOOL_ROOT:-/app/spool}"
LIB="${ROOT}/lib/spool"

cp /solution/fixed/acl.py "${LIB}/acl.py"
cp /solution/fixed/paths.py "${LIB}/paths.py"
cp /solution/fixed/quota.py "${LIB}/quota.py"
cp /solution/fixed/vfs.py "${LIB}/vfs.py"
cp /solution/fixed/cli.py "${LIB}/cli.py"

# Re-open the store through the public CLI so var/ exists after the patch.
rm -f "${ROOT}/var/spool.db"
"${ROOT}/bin/spoolctl" --identity root --tenant acme quota >/dev/null
"${ROOT}/bin/spoolctl" --identity root --tenant globex quota >/dev/null
