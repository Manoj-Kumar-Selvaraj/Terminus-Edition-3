#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fixed="$here/fixed"
target=/app/wire/src/copybooks

install -m 0644 "$fixed/transaction-begin" "$target/transaction-begin"
install -m 0644 "$fixed/request-identity" "$target/request-identity"
install -m 0644 "$fixed/dual-control-check" "$target/dual-control-check"
install -m 0644 "$fixed/twin-post" "$target/twin-post"
install -m 0644 "$fixed/freeze-gate" "$target/freeze-gate"

/app/wire/bin/build-wire
