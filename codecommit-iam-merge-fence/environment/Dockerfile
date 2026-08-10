# Canonical Terminus Python base (digest-pinned).
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="codecommit-iam-merge-fence" \
      org.opencontainers.image.description="Local CodeCommit IAM evaluator, FF merge fence, pipeline journal" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/codecommit/lib

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        git \
        tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/codecommit

COPY codecommit/ /app/codecommit/

RUN chmod 0755 /app/codecommit/bin/ccctl \
    && mkdir -p /app/codecommit/var/repos \
    && python3 /app/codecommit/lib/cc/seed.py

CMD ["sleep", "infinity"]
