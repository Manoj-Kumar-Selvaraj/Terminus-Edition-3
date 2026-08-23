#!/usr/bin/env bash
set -euo pipefail

ROOT="${PII_HOME:-/app/enterprise-pii}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED="$HERE/fixed"

install -m 0644 "$FIXED/internal/api/http.go" "$ROOT/internal/api/http.go"
install -m 0644 "$FIXED/internal/ingest/store.go" "$ROOT/internal/ingest/store.go"
install -m 0644 "$FIXED/internal/service/service.go" "$ROOT/internal/service/service.go"
install -m 0644 "$FIXED/internal/scheduler/scheduler.go" "$ROOT/internal/scheduler/scheduler.go"
install -m 0644 "$FIXED/internal/persistence/snapshot.go" "$ROOT/internal/persistence/snapshot.go"
install -m 0644 "$FIXED/internal/report/publisher.go" "$ROOT/internal/report/publisher.go"
install -m 0644 "$FIXED/internal/protocol/worker.go" "$ROOT/internal/protocol/worker.go"
install -m 0644 "$FIXED/internal/report/report.go" "$ROOT/internal/report/report.go"
install -m 0644 "$FIXED/internal/registry/registry.go" "$ROOT/internal/registry/registry.go"

JFIX="$FIXED/worker/src/main/java/com/example/pii"
JTGT="$ROOT/worker/src/main/java/com/example/pii"
install -m 0644 "$JFIX/WorkerMain.java" "$JTGT/WorkerMain.java"
install -m 0644 "$JFIX/ScannerEngine.java" "$JTGT/ScannerEngine.java"
install -m 0644 "$JFIX/policy/ScanPolicy.java" "$JTGT/policy/ScanPolicy.java"
install -m 0644 "$JFIX/text/UnicodeChunker.java" "$JTGT/text/UnicodeChunker.java"
install -m 0644 "$JFIX/protocol/Protocol.java" "$JTGT/protocol/Protocol.java"
install -m 0644 "$JFIX/detect/Detection.java" "$JTGT/detect/Detection.java"
install -m 0644 "$JFIX/privacy/Evidence.java" "$JTGT/privacy/Evidence.java"
install -m 0644 "$JFIX/read/TextAndPropertiesReaders.java" "$JTGT/read/TextAndPropertiesReaders.java"

cd "$ROOT"
"$ROOT/scripts/build.sh"
"$ROOT/bin/pii-control" recover --config "$ROOT/config/system.json" || true
