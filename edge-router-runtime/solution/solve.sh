#!/bin/bash
set -euo pipefail
cp /solution/main.go /app/edge-router/main.go
cd /app/edge-router
gofmt -w main.go
go test ./...
go build -o edge-router .
