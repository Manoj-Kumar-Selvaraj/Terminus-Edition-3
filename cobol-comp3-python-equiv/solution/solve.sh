#!/usr/bin/env bash
set -euo pipefail
cp -a /solution/fixed/. /app/equiv/src/
install -m 0644 /solution/fixed/schema.sql /app/equiv/sql/schema.sql
