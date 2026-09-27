FROM python:3.12-slim-bookworm@sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema tmux postgresql-client ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY src/ /app/
COPY sql/ /app/sql/
COPY bin/ /app/bin/
COPY docs/ /app/docs/
RUN chmod 0755 /app/bin/* && mkdir -p /app/state/evidence /app/out
ENTRYPOINT ["/app/bin/forensicd"]
