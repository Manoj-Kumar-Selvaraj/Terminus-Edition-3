FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

ARG NATS_SERVER_VERSION=2.14.3
ARG NATS_SERVER_DEB_SHA256=e0c053fc2abe991f17b2be794897bb3f94ca1857bf886498c741ba69fb62522a

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip sqlite3 curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL -o /tmp/nats-server.deb "https://github.com/nats-io/nats-server/releases/download/v${NATS_SERVER_VERSION}/nats-server-v${NATS_SERVER_VERSION}-amd64.deb" \
 && echo "${NATS_SERVER_DEB_SHA256}  /tmp/nats-server.deb" | sha256sum -c - \
 && dpkg -i /tmp/nats-server.deb \
 && rm -f /tmp/nats-server.deb \
 && python3 -m pip install --break-system-packages pytest==8.4.1 nats-py==2.15.0 \
 && mkdir -p /app/continuity /logs/verifier /tests

COPY test_continuity.py /tests/test_continuity.py
COPY test_contract_coverage.py /tests/test_contract_coverage.py
COPY test.sh /tests/test.sh
RUN chmod +x /tests/test.sh

WORKDIR /app/continuity
