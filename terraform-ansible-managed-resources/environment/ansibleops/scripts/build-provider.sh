#!/usr/bin/env bash
set -euo pipefail

ROOT="${ANSIBLEOPS_ROOT:-/app/ansibleops}"
VERSION="0.1.0"
TARGET="/opt/terraform/plugins/registry.terraform.io/local/ansibleops/${VERSION}/linux_amd64"
BINARY="${TARGET}/terraform-provider-ansibleops_v${VERSION}"

mkdir -p "${TARGET}"
cd "${ROOT}"

gofmt -w ./cmd ./internal
GOTOOLCHAIN=local go build \
  -trimpath \
  -ldflags "-s -w -X main.version=${VERSION}" \
  -o "${BINARY}" \
  ./cmd/terraform-provider-ansibleops
chmod 0755 "${BINARY}"
printf 'provider=%s\n' "${BINARY}"
