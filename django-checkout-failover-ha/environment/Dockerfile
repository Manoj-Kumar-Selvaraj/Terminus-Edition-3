FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="Django checkout HA lab"
LABEL org.opencontainers.image.version="1.0"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      sqlite3 \
      curl \
      ca-certificates \
      tmux \
      asciinema \
      procps \
      patch \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/ha
COPY ha/ /app/ha/

RUN python3 -m venv /opt/ha-venv \
 && /opt/ha-venv/bin/pip install --no-cache-dir --upgrade "pip==25.2" \
 && /opt/ha-venv/bin/pip install --no-cache-dir "Django==4.2.23" "pytest==8.4.1" "pytest-json-ctrf==0.3.5" \
 && mkdir -p /app/ha/state /app/ha/out /app/ha/notes /app/ha/logs/captured \
 && chmod +x /app/ha/bin/* /app/ha/sql/generate_seed.py \
 && sqlite3 /app/ha/state/primary.sqlite < /app/ha/sql/schema.sql \
 && sqlite3 /app/ha/state/primary.sqlite < /app/ha/sql/seed.sql \
 && sqlite3 /app/ha/state/standby.sqlite < /app/ha/sql/schema.sql \
 && sqlite3 /app/ha/state/standby.sqlite < /app/ha/sql/standby_seed.sql

ENV PATH="/opt/ha-venv/bin:${PATH}"
ENV PYTHONPATH="/app/ha"
ENV HA_ROOT="/app/ha"
ENV DJANGO_SETTINGS_MODULE="shopdesk.settings"
