# Separate verifier image (environment_mode=separate).
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="yard-gate-dock-dwell-control-verifier" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    YARD_ROOT=/app/yard

COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --no-deps -r /tmp/requirements.lock \
    && rm -f /tmp/requirements.lock \
    && mkdir -p /app/yard/out /app/yard/var /logs/verifier

COPY test.sh test_outputs.py /tests/
RUN chmod 0755 /tests/test.sh

WORKDIR /app
