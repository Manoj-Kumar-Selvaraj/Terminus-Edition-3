#!/usr/bin/env bash
# Optional helper: ensure schema + default org without starting HTTP.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export STACKYARD_ROOT="$ROOT"
export STACKYARD_DB="${STACKYARD_DB:-$ROOT/data/stackyard.db}"
mkdir -p "$(dirname "$STACKYARD_DB")" "$ROOT/data/workspaces"
if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 not installed; server migrate path will seed on boot" >&2
  exit 0
fi
sqlite3 "$STACKYARD_DB" < "$ROOT/db/schema.sql"
COUNT="$(sqlite3 "$STACKYARD_DB" "SELECT COUNT(*) FROM organizations WHERE slug='acme';")"
if [ "$COUNT" = "0" ]; then
  NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sqlite3 "$STACKYARD_DB" "INSERT INTO organizations(id,name,slug,created_at) VALUES('org_seed_acme','acme','acme','$NOW');"
fi
echo "seeded $STACKYARD_DB"
