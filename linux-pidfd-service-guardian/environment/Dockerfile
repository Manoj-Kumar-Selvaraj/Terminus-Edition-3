FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c

LABEL org.opencontainers.image.title="linux-service-guardian" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.created="2026-08-02T00:00:00Z"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        cmake \
        ninja-build \
        patch \
        procps \
        tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/guardian

COPY CMakeLists.txt /app/guardian/CMakeLists.txt
COPY include/ /app/guardian/include/
COPY src/ /app/guardian/src/
COPY docs/ /app/guardian/docs/
COPY bin/ /app/guardian/bin/

RUN chmod 0755 /app/guardian/bin/build-guardian \
    && /app/guardian/bin/build-guardian

CMD ["sleep", "infinity"]
