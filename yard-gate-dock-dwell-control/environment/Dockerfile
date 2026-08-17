# Canonical Terminus Python base (digest-pinned).
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="yard-gate-dock-dwell-control" \
      org.opencontainers.image.description="DC yard gate-to-dock dwell control plane" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/yard \
    YARD_ROOT=/app/yard

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        tmux \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/yard

COPY yard/ /app/yard/

RUN python3 /app/yard/cmd/seed.py \
    && chmod 0755 /app/yard/bin/yardctl /app/yard/bin/seed

CMD ["sleep", "infinity"]
