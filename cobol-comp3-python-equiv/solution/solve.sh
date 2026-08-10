#!/usr/bin/env bash
set -euo pipefail

install -m 0644 /solution/fixed/unpack.py /app/equiv/src/unpack.py
/app/equiv/bin/equiv-eval
