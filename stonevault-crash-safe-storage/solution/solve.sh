#!/bin/bash
set -euo pipefail
cd /app/stonevault
patch -p1 < /oracle/fix.patch
make clean
make
