#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"

pg_ctlcluster 15 main start
runuser -u postgres -- psql -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE workshop_app LOGIN PASSWORD 'workshop_local';
CREATE DATABASE workshop OWNER workshop_app;
SQL

export WORKSHOP_DB_HOST=127.0.0.1
export WORKSHOP_DB=workshop@127.0.0.1:5432
export WORKSHOP_DB_USER=workshop_app
export WORKSHOP_DB_PASSWORD=workshop_local

pytest --ctrf /logs/verifier/ctrf.json -p no:cacheprovider "$TEST_DIR" -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
