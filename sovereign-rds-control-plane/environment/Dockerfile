FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="sovereign-rds-control-plane" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/rds \
    PATH=/app/rds/bin:$PATH \
    RDS_HOME=/app/rds

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    tmux \
    asciinema \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/rds

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rds/ ./rds/
COPY bin/ ./bin/
COPY config/ ./config/
COPY db/ ./db/
COPY docs/ ./docs/

RUN sed -i 's/\r$//' bin/* \
    && chmod +x bin/* \
    && mkdir -p /app/rds/out /app/rds/state/checkpoints

CMD ["/app/rds/bin/rdsd"]
