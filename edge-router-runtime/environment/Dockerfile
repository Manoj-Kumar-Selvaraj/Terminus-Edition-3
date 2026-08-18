FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.source="https://github.com/Manoj-Kumar-Selvaraj/Terminus-Edition-3" \
      org.opencontainers.image.version="3.0" \
      org.opencontainers.image.licenses="MIT"

RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema ca-certificates curl jq \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/edge-router
COPY go.mod ./go.mod
COPY cmd ./cmd
COPY internal ./internal
COPY config.json ./config.json
COPY docs ./docs
RUN gofmt -w cmd internal \
    && go test ./... \
    && go build -trimpath -ldflags='-s -w' -o /usr/local/bin/edge-router-runtime ./cmd/edge-router-runtime \
    && mkdir -p /var/lib/edge-router

WORKDIR /app
ENV EDGE_ROUTER_CONFIG=/app/edge-router/config.json \
    EDGE_ROUTER_STATE_DIR=/var/lib/edge-router
CMD ["bash"]
