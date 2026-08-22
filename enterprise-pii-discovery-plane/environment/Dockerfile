FROM ubuntu:24.04@sha256:7c06e91f61fa88c08cc74f7e1b7c69ae24910d745357e0dfe1d2c0322aaf20f9

LABEL org.opencontainers.image.title="enterprise-pii-discovery-plane" \
      org.opencontainers.image.description="Offline enterprise PII discovery control plane and scanner" \
      org.opencontainers.image.version="0.1.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PII_HOME=/app/enterprise-pii \
    PII_CONFIG=/app/enterprise-pii/config/system.json

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        bash \
        ca-certificates \
        golang-go \
        make \
        maven \
        openjdk-21-jdk-headless \
        python3 \
        tmux \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/enterprise-pii
COPY enterprise-pii/ /app/enterprise-pii/
RUN /app/enterprise-pii/scripts/build.sh \
    && /app/enterprise-pii/bin/generate-corpus --output /app/enterprise-pii/corpus --records 12000 \
    && mkdir -p /app/enterprise-pii/state/generations /app/enterprise-pii/reports \
    && chmod 0755 /app/enterprise-pii/bin/* /app/enterprise-pii/scripts/*.sh

CMD ["/app/enterprise-pii/scripts/run-control.sh"]