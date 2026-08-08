FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

LABEL org.opencontainers.image.title="Payments EOD batch control"
LABEL org.opencontainers.image.version="3.0"

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      gnucobol \
      sqlite3 \
      tmux \
      asciinema \
      jq \
      patch \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/eod
COPY eod/ /app/eod/
RUN mkdir -p /app/eod/state /app/eod/out /app/eod/.bin \
 && chmod +x /app/eod/bin/run_eod.sh /app/eod/lib/*.sh \
 && sqlite3 /app/eod/state/payment_eod.db < /app/eod/sql/schema.sql \
 && sqlite3 /app/eod/state/payment_eod.db < /app/eod/sql/seed.sql
