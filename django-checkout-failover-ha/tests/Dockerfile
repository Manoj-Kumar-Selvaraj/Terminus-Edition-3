FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV HA_VERIFIER_REV=4

RUN apt-get update \
 && apt-get install -y --no-install-recommends sqlite3 \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5 Django==4.2.23 \
 && python3 -c "import pytest, django" \
 && mkdir -p /app/ha /tests

COPY test_outputs.py /tests/test_outputs.py
COPY test.sh /tests/test.sh
RUN chmod +x /tests/test.sh

WORKDIR /app/ha
