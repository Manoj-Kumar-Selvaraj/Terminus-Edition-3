FROM ubuntu:24.04@sha256:7c06e91f61fa88c08cc74f7e1b7c69ae24910d745357e0dfe1d2c0322aaf20f9

LABEL org.opencontainers.image.source="local/sovereign-l4-load-balancer" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       asciinema bash ca-certificates cmake g++ golang-go make ninja-build \
       pkg-config python3 python3-venv tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY sovereign-lb /app/sovereign-lb
RUN chmod 0755 /app/sovereign-lb/bin/* /app/sovereign-lb/tools/lab/*.py \
    && /app/sovereign-lb/bin/build

ENV SOVEREIGN_LB_HOME=/app/sovereign-lb
ENTRYPOINT ["/app/sovereign-lb/bin/lb-control-plane"]