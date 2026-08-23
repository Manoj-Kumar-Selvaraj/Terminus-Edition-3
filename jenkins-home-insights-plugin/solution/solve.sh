#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET=${PLUGIN_ROOT:-/app/plugin}

if [ ! -d "$TARGET" ]; then
    printf '%s\n' "missing plugin directory: $TARGET" >&2
    exit 1
fi

(
    cd "$ROOT/fixed"
    find . -type f -print | LC_ALL=C sort | while IFS= read -r relative; do
        destination="$TARGET/${relative#./}"
        mkdir -p "$(dirname -- "$destination")"
        cp "$relative" "$destination"
    done
)

printf '%s\n' "operational insights reference repair installed"