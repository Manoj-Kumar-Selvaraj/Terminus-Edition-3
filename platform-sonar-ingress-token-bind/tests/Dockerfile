FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl \
      sqlite3 \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir "pytest==8.4.1" "PyYAML==6.0.2" "pytest-json-ctrf==0.3.5"

RUN mkdir -p /app/platform/stack /app/platform/var /app/platform/ops /tests /opt/platform-engine

COPY test.sh /tests/test.sh
COPY test_outputs.py /tests/test_outputs.py
COPY engine/ /opt/platform-engine/
RUN chmod +x /tests/test.sh

ENV PLATFORM_ROOT=/app/platform
ENV PYTHONPATH=/opt/platform-engine
WORKDIR /app/platform
