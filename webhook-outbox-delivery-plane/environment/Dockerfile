# Canonical Go toolchain image for the outbox agent environment.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="webhook-outbox-delivery-plane" \
      org.opencontainers.image.description="Incomplete webhook outbox delivery plane for Terminus 3." \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    GOPROXY=https://proxy.golang.org,direct \
    OUTBOX_ROOT=/app/outbox

WORKDIR /app/outbox

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        bash \
        ca-certificates \
        curl \
        sqlite3 \
        tmux \
    && rm -rf /var/lib/apt/lists/*

COPY outbox/ /app/outbox/

RUN chmod 0755 /app/outbox/scripts/seed.sh \
    && go mod tidy \
    && go build -o /app/outbox/bin/outboxd ./cmd/outboxd \
    && go build -o /app/outbox/bin/outboxctl ./cmd/outboxctl \
    && go build -o /app/outbox/bin/seed ./cmd/seed \
    && mkdir -p /app/outbox/data \
    && OUTBOX_ROOT=/app/outbox OUTBOX_DB=/app/outbox/data/outbox.db OUTBOX_DATA=/app/outbox/data /app/outbox/bin/seed

WORKDIR /app/outbox
