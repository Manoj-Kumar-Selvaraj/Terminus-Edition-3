#!/bin/bash
set -euo pipefail

patch --no-backup-if-mismatch -p1 -d /app/guardian < /solution/fix.patch
/app/guardian/bin/build-guardian
