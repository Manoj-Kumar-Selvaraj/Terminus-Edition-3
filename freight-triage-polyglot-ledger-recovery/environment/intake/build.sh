#!/usr/bin/env bash
# Compile the freight intake service with the JDK only. No external artifacts.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$here/build"
mkdir -p "$here/build/classes"

find "$here/src" -name '*.java' | LC_ALL=C sort > "$here/build/sources.txt"
javac -encoding UTF-8 -nowarn -d "$here/build/classes" "@$here/build/sources.txt"

echo "intake: compiled $(wc -l < "$here/build/sources.txt") java sources"
