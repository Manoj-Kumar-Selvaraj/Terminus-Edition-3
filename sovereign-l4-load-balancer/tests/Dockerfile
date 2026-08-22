# Verifier shares the agent glibc/toolchain so prebuilt Go/C++ binaries execute.
FROM sovereign-l4-lb-env

LABEL org.opencontainers.image.title="sovereign-l4-load-balancer-verifier" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOVEREIGN_LB_HOME=/app/sovereign-lb

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --break-system-packages --no-deps -r /tmp/requirements.lock \
    && rm -f /tmp/requirements.lock \
    && mkdir -p /logs/verifier

COPY test.sh test_outputs.py /tests/
RUN chmod 0755 /tests/test.sh

WORKDIR /app
ENTRYPOINT []
CMD ["/tests/test.sh"]
