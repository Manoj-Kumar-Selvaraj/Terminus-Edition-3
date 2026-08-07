# Fleet harden lab: Ansible control + three logical edge instance roots on one host.
# Debian bookworm is the Ansible/ops runtime; python stubs stand in for offline
# audit/metrics/promtail/falco adapters the contract names.
FROM public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d

LABEL org.opencontainers.image.title="ansible-fleet-security-observability" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.created="2026-08-02T00:00:00Z"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        openssh-client \
        procps \
        psmisc \
        python3 \
        python3-pip \
        python3-apt \
        sudo \
        tmux \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
        ansible-core==2.17.6

WORKDIR /app

COPY bin/fleet-harden-apply /app/bin/fleet-harden-apply
COPY docs/ /app/environment/docs/
COPY evidence/ /app/environment/evidence/
COPY ansible/ /app/environment/ansible/

RUN chmod 0755 /app/bin/fleet-harden-apply \
    && chmod -R go-w /app/environment /app/bin \
    && mkdir -p /app/var/fleet-harden /app/edges/app /app/edges/data /app/edges/ops /var/log
