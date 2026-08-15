#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
python3 -m pytest /tests -q
if [ $? -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; fi
