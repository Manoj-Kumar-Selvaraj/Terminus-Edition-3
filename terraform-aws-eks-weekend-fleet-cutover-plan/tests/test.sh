#!/bin/bash
# -e is deliberately omitted so a pytest failure still reaches the reward block.
set -uo pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

TEST_DIR="${TEST_DIR:-/tests}"
cd "$TEST_DIR"

pytest --ctrf /logs/verifier/ctrf.json \
  "$TEST_DIR/test_plan_provenance.py" \
  "$TEST_DIR/test_control_plane.py" \
  "$TEST_DIR/test_iam.py" \
  "$TEST_DIR/test_addons_helm.py" \
  "$TEST_DIR/test_artifactory_credentials.py" \
  "$TEST_DIR/test_monitoring_scheduler.py" \
  "$TEST_DIR/test_ingress_outputs.py" \
  "$TEST_DIR/test_cross_links.py" \
  "$TEST_DIR/test_cutover_timeline.py" \
  -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
