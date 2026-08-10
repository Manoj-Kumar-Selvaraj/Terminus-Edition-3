FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ENV HA_VERIFIER_REV=3

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip sqlite3 \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m pip install --break-system-packages pytest==8.4.1 Django==4.2.23 \
 && python3 -c "import pytest, django" \
 && mkdir -p /app/ha /tests

COPY test_ha.py /tests/test_ha.py
COPY test.sh /tests/test.sh
RUN chmod +x /tests/test.sh

WORKDIR /app/ha
