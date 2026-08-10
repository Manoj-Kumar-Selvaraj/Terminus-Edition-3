FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

LABEL org.opencontainers.image.title="Django checkout HA lab"
LABEL org.opencontainers.image.version="1.0"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 \
      python3-venv \
      python3-pip \
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
 && /opt/ha-venv/bin/pip install --no-cache-dir "Django==4.2.23" "pytest==8.4.1" \
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
