FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

LABEL org.opencontainers.image.title="Terminus payment EOD COBOL batch" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.licenses="MIT"

RUN apt-get update \
 && apt-get install -y --no-install-recommends gnucobol sqlite3 tmux asciinema jq ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/eod
COPY eod/ /app/eod/
RUN mkdir -p /app/eod/state \
 && chmod +x /app/eod/bin/run_eod.sh \
 && sqlite3 /app/eod/state/payment_eod.db < /app/eod/sql/schema.sql \
 && sqlite3 /app/eod/state/payment_eod.db < /app/eod/sql/seed.sql
