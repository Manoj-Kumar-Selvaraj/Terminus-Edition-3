#!/usr/bin/env bash
set -euo pipefail
ROOT="${PII_HOME:-/app/enterprise-pii}"
exec "$ROOT/bin/pii-control" serve --config "${PII_CONFIG:-$ROOT/config/system.json}"