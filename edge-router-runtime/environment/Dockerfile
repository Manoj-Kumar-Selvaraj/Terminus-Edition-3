FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.source="https://github.com/Manoj-Kumar-Selvaraj/Terminus-Edition-3" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.licenses="MIT"

RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/edge-router
COPY go.mod /app/edge-router/go.mod
COPY main.go /app/edge-router/main.go
COPY config.json /app/edge-router/config.json
COPY CONTRACT.md /app/edge-router/CONTRACT.md
RUN go build -o /usr/local/bin/edge-router .

WORKDIR /app
CMD ["bash"]
