# Verifier rebuilds and exercises the submitted Stackyard tree.
# Go canonical base plus Python/pytest for Harbor grading.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="stackyard-terraform-control-plane-verifier" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOPROXY=https://proxy.golang.org,direct

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        python3 \
        python3-pip \
        python3-venv \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    requests==2.32.4 \
    && python3 -c "import pytest, requests; print('pytest', pytest.__version__)"

# Parent directories for declared artifacts. Do not create /logs/verifier here.
RUN mkdir -p /app/stackyard

# Separate mode does not upload tests/; the image must own /tests.
COPY . /tests/
RUN chmod 0755 /tests/test.sh

WORKDIR /app
