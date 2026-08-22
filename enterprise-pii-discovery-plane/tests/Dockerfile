FROM ubuntu:24.04@sha256:7c06e91f61fa88c08cc74f7e1b7c69ae24910d745357e0dfe1d2c0322aaf20f9

LABEL org.opencontainers.image.title="enterprise-pii-discovery-plane-verifier" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PII_HOME=/app/enterprise-pii \
    PII_CONFIG=/app/enterprise-pii/config/system.json

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        golang-go \
        maven \
        openjdk-21-jdk-headless \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --break-system-packages --no-deps -r /tmp/requirements.lock \
    && rm -f /tmp/requirements.lock

RUN mkdir -p /app/enterprise-pii /logs/verifier /tests

COPY conftest.py test_outputs.py test.sh /tests/
COPY fixtures /tests/fixtures
RUN chmod 0755 /tests/test.sh

WORKDIR /app/enterprise-pii
