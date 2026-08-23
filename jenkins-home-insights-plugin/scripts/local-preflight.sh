#!/usr/bin/env bash
# Local preflight when Docker/Harbor are unavailable. Copies plugin to /app/plugin without mutating the task tree.
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
MODE="${1:-oracle}" # oracle | starter | compile-only
WORKDIR="${TMPDIR:-/tmp}/jh-insights-preflight-$$"
PLUGIN="/app/plugin"
TESTS="$ROOT/tests"

resolve_java_home() {
  if [[ -n "${JAVA_HOME:-}" && -x "${JAVA_HOME}/bin/javac" ]]; then
    return 0
  fi
  for candidate in \
    "/c/Program Files/Eclipse Adoptium/jdk-17.0.10.7-hotspot" \
    "/c/Program Files/Eclipse Adoptium/jdk-17"* \
    "/c/Program Files/Java/jdk-17"* \
    "/c/Program Files/Microsoft/jdk-17"*; do
    if [[ -x "$candidate/bin/javac" ]]; then
      export JAVA_HOME="$candidate"
      return 0
    fi
  done
  return 1
}

cleanup() { rm -rf "$WORKDIR" "$PLUGIN"; }
trap cleanup EXIT

if ! resolve_java_home; then
  echo "error: JDK 17+ with javac is required for local preflight" >&2
  echo "hint: install Temurin 17 and set JAVA_HOME, or run Harbor/Docker verifier" >&2
  exit 127
fi
export PATH="$JAVA_HOME/bin:$PATH"

mkdir -p /app
rm -rf "$PLUGIN"
cp -a "$ROOT/environment/plugin" "$PLUGIN"

if [[ "$MODE" == "oracle" ]]; then
  PLUGIN_ROOT="$PLUGIN" sh "$ROOT/solution/solve.sh"
fi

cd "$PLUGIN"
sh bin/build-core

if [[ "$MODE" == "compile-only" ]]; then
  echo "compile-only PASS"
  exit 0
fi

python -m pytest "$TESTS/test_outputs.py" -q --tb=line -rA
exit $?
