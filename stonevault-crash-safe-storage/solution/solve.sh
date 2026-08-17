#!/bin/bash
set -euo pipefail
cd /app/stonevault
patch -p1 < /solution/fix.patch
make clean
make
