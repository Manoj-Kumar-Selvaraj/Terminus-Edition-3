#!/usr/bin/env bash
set -euo pipefail
ROOT="${PII_HOME:-/app/enterprise-pii}"
exec "$ROOT/bin/pii-worker" --config "${PII_CONFIG:-$ROOT/config/system.json}"