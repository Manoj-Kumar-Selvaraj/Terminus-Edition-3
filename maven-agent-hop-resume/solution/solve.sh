#!/usr/bin/env bash
set -euo pipefail

install -m 0644 /solution/fixed/agents.py /app/reactor/engine/agents.py
install -m 0644 /solution/fixed/library.py /app/reactor/engine/library.py
install -m 0644 /solution/fixed/archive.py /app/reactor/engine/archive.py
install -m 0644 /solution/fixed/runner.py /app/reactor/engine/runner.py

/app/reactor/bin/pipe resume
/app/reactor/bin/pipe status >/dev/null
