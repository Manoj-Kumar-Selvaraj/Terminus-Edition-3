#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fixed="$here/fixed"
target=/app/workshop/src/copybooks

install -m 0644 "$fixed/transaction-begin" "$target/transaction-begin"
install -m 0644 "$fixed/request-identity" "$target/request-identity"
install -m 0644 "$fixed/resource-lock" "$target/resource-lock"
install -m 0644 "$fixed/overlap-check" "$target/overlap-check"
install -m 0644 "$fixed/move-transaction" "$target/move-transaction"

/app/workshop/bin/build-workshop
