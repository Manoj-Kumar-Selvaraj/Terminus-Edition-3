FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

LABEL org.opencontainers.image.title="ansible-fleet-security-observability-verifier" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.created="2026-08-02T00:00:00Z"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        procps \
        psmisc \
        python3 \
        python3-apt \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
        ansible-core==2.17.6 \
        pytest==8.3.4 \
        pytest-json-ctrf==0.3.5 \
        requests==2.32.3

# Parent dirs for declared artifacts; bake evidence/docs/apply for re-probe/re-apply.
RUN mkdir -p \
        /app/var/fleet-harden \
        /app/edges \
        /app/environment/ansible \
        /app/environment/docs \
        /app/environment/evidence \
        /app/bin \
        /logs/verifier \
        /tests

COPY fixtures/evidence/ /app/environment/evidence/
COPY fixtures/docs/ /app/environment/docs/
COPY fixtures/bin/fleet-harden-apply /app/bin/fleet-harden-apply
COPY test.sh test_outputs.py /tests/

RUN chmod 0755 /app/bin/fleet-harden-apply /tests/test.sh

WORKDIR /app
