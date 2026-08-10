# Canonical Terminus Python base (digest-pinned).
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="wiki-creation-counter-flap" \
      org.opencontainers.image.description="Wiki users/posts API with probe and creation-counter flap" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/wiki \
    WIKI_ROOT=/app/wiki \
    WIKI_DB=/app/wiki/var/wiki.db

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/wiki

COPY wiki/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY wiki/ /app/wiki/

RUN chmod 0755 /app/wiki/bin/wikictl \
    && mkdir -p /app/wiki/var /app/wiki/out \
    && python3 /app/wiki/bin/wikictl seed

CMD ["sleep", "infinity"]
