#!/usr/bin/env bash
set -euo pipefail
ROOT="${PII_HOME:-/app/enterprise-pii}"
mkdir -p "$ROOT/bin"
cd "$ROOT"
go build -trimpath -o bin/pii-control ./cmd/pii-control
go build -trimpath -o bin/piictl ./cmd/piictl
mvn -q -f worker/pom.xml -DskipTests package
cp worker/target/pii-worker-0.1.0.jar bin/pii-worker.jar
cat > bin/pii-worker <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${PII_HOME:-/app/enterprise-pii}"
exec java -jar "$ROOT/bin/pii-worker.jar" "$@"
EOF
cat > bin/generate-corpus <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${PII_HOME:-/app/enterprise-pii}"
exec python3 "$ROOT/tools/generate_corpus.py" "$@"
EOF
chmod 0755 bin/pii-worker bin/generate-corpus