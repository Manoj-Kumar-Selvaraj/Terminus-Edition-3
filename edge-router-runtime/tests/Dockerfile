FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --break-system-packages --no-cache-dir pytest==8.3.5

RUN mkdir -p /app/edge-router /logs/verifier /tests
COPY test_outputs.py /tests/test_outputs.py
COPY test.sh /tests/test.sh
RUN chmod +x /tests/test.sh

WORKDIR /app/edge-router
