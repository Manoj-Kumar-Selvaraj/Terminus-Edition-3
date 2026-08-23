#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET=${FLUIDLAB_ROOT:-/app/fluidlab}

if [ ! -d "$TARGET" ]; then
    printf '%s\n' "missing fluidlab directory: $TARGET" >&2
    exit 1
fi

(
    cd "$ROOT/fixed/src/fluidlab"
    find . -type f -name '*.py' -print | LC_ALL=C sort | while IFS= read -r relative; do
        destination="$TARGET/src/fluidlab/${relative#./}"
        mkdir -p "$(dirname -- "$destination")"
        cp "$relative" "$destination"
    done
)

find "$TARGET/src/fluidlab" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

printf '%s\n' "fluidlab reference repair installed"
