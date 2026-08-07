# Separate verifier image.
#
# The suite is graded by rebuilding the agent's own sources and re-running the
# three CLIs, so this image carries the same three toolchains as the agent image
# plus a pinned pytest with the CTRF reporter. Same canonical bookworm base.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="freight-triage-polyglot-ledger-recovery-verifier" \
      org.opencontainers.image.version="2" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        binutils \
        ca-certificates \
        g++ \
        golang-go \
        make \
        openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --no-deps -r /tmp/requirements.lock \
    && rm -f /tmp/requirements.lock

ENV GOPATH=/opt/gocache/gopath \
    GOCACHE=/opt/gocache/go-build \
    GOFLAGS=-mod=mod \
    GOPROXY=off \
    CGO_ENABLED=0

# Parent directories for every declared artifact path plus the reward location.
RUN mkdir -p /app /app/output /app/bin /app/environment /logs/verifier /tests \
    && mkdir -p /opt/gocache/gopath /opt/gocache/go-build \
    && chmod -R 0777 /opt/gocache

# Separate-verifier mode skips host upload of tests/; bake them into the image.
COPY test.sh test_outputs.py /tests/
RUN chmod 0755 /tests/test.sh

WORKDIR /app
