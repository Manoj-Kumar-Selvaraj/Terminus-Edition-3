FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="platform-sonar-ingress-token-bind"
LABEL org.opencontainers.image.version="1.0"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      tmux \
      asciinema \
      curl \
      sqlite3 \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "PyYAML==6.0.2"

WORKDIR /app/platform
COPY platform/ /app/platform/

RUN mkdir -p /app/platform/var/efs /app/platform/var/dns /app/platform/var/ssm \
 && sqlite3 /app/platform/var/platform.db < /app/platform/sql/schema.sql \
 && sqlite3 /app/platform/var/platform.db < /app/platform/sql/seed.sql \
 && chmod +x /app/platform/scripts/reload /app/platform/scripts/validate.sh

ENV PLATFORM_ROOT=/app/platform
ENV PYTHONPATH=/app/platform
ENV PATH="/app/platform/scripts:${PATH}"
