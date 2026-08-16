# Canonical Go toolchain image for the Stackyard agent environment.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="stackyard-terraform-control-plane" \
      org.opencontainers.image.description="Incomplete Stackyard Terraform control plane for Terminus 3." \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    GOPROXY=https://proxy.golang.org,direct \
    STACKYARD_ROOT=/app/stackyard

WORKDIR /app/stackyard

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        bash \
        ca-certificates \
        curl \
        sqlite3 \
        tmux \
    && rm -rf /var/lib/apt/lists/*

COPY stackyard/ /app/stackyard/

RUN chmod 0755 /app/stackyard/bin/terraform-shim /app/stackyard/scripts/seed.sh \
    && go mod tidy \
    && go build -o /app/stackyard/bin/stackyard ./cmd/stackyard \
    && mkdir -p /app/stackyard/data/workspaces

WORKDIR /app/stackyard
