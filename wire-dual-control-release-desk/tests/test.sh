#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"

pg_ctlcluster 15 main start
runuser -u postgres -- psql -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE wire_app LOGIN PASSWORD 'wire_local';
CREATE DATABASE wire OWNER wire_app;
SQL

export WIRE_DB_HOST=127.0.0.1
export WIRE_DB=wire@127.0.0.1:5432
export WIRE_DB_USER=wire_app
export WIRE_DB_PASSWORD=wire_local

pytest --ctrf /logs/verifier/ctrf.json -p no:cacheprovider "$TEST_DIR" -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
