# Agent image for the freight triage polyglot stack.
#
# The stack is a C++17 engine, a JDK-only Java service and a Go reconciler that
# are driven from bash. python:3.13-slim-bookworm is the canonical Debian
# bookworm base carried by the sanctioned image list, and the three language
# toolchains are added from the bookworm archive so a single runtime hosts all
# of them; no single-language canonical base can build this stack.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="freight-triage-polyglot-ledger-recovery" \
      org.opencontainers.image.description="Broken C++/Java/Go freight triage ledger stack" \
      org.opencontainers.image.version="2" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        asciinema \
        binutils \
        ca-certificates \
        g++ \
        golang-go \
        make \
        openjdk-17-jdk-headless \
        tmux \
    && rm -rf /var/lib/apt/lists/*

# The Go module has no third party dependencies, so the reconciler builds with
# the proxy switched off and stays reproducible without a network.
ENV GOPATH=/app/.cache/gopath \
    GOCACHE=/app/.cache/go-build \
    GOFLAGS=-mod=mod \
    GOPROXY=off \
    CGO_ENABLED=0 \
    PATH=/app/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /app

# Small, startup critical layers first.
COPY bin/ /app/environment/bin/
COPY docs/ /app/environment/docs/
COPY data/ /app/environment/data/
COPY native/ /app/environment/native/
COPY intake/ /app/environment/intake/
COPY reconcile/ /app/environment/reconcile/

RUN mkdir -p /app/bin /app/output /app/.cache/go-build /app/.cache/gopath \
    && cp /app/environment/bin/run-freight-suite /app/bin/run-freight-suite \
    && cp /app/environment/bin/freightctl /app/bin/freightctl \
    && cp /app/environment/bin/freight-intake /app/bin/freight-intake \
    && cp /app/environment/bin/freight-reconcile /app/bin/freight-reconcile \
    && chmod 0755 /app/bin/run-freight-suite /app/bin/freightctl /app/bin/freight-intake \
        /app/bin/freight-reconcile /app/environment/intake/build.sh \
    && chmod -R 0777 /app/.cache

CMD ["sleep", "infinity"]
