#!/usr/bin/env bash
set -euo pipefail
export JOBS_DIR=/tmp/e3-yard
export PATH="/root/.local/bin:${PATH}"
mkdir -p "$JOBS_DIR"
exec bash /mnt/d/Manoj/Projects/Portfolio/TerminalBench/Terminus-Edition-3/terminus3.sh oracle yard-gate-dock-dwell-control
