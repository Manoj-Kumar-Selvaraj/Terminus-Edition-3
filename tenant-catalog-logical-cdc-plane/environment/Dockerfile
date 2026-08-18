# Canonical Go toolchain image for the catalog agent environment.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="tenant-catalog-logical-cdc-plane" \
      org.opencontainers.image.description="Snapshot catalog with logical CDC and replica apply" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    GOPROXY=https://proxy.golang.org,direct \
    CATALOG_ROOT=/app/catalog

WORKDIR /app/catalog

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        bash \
        ca-certificates \
        sqlite3 \
        tmux \
    && rm -rf /var/lib/apt/lists/*

COPY catalog/ /app/catalog/

RUN mkdir -p /app/catalog/bin /app/catalog/data /app/catalog/out /app/catalog/warehouse \
    && go build -mod=readonly -o /app/catalog/bin/catalogctl ./cmd/catalogctl \
    && go build -mod=readonly -o /app/catalog/bin/seed ./cmd/seed \
    && CATALOG_ROOT=/app/catalog /app/catalog/bin/seed

WORKDIR /app
CMD ["sleep", "infinity"]
