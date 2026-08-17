FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="EC2 artifact policy enforcement lab"
LABEL org.opencontainers.image.version="1.0"

RUN apt-get update \
 && apt-get install -y --no-install-recommends golang-go ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m pip install --no-cache-dir "pytest==8.4.1" "pytest-json-ctrf==0.3.5"

WORKDIR /app/enforcer
COPY enforcer/ /app/enforcer/
RUN go build -o /usr/local/bin/artifactguard ./cmd/artifactguard \
 && mkdir -p /app/enforcer/state /app/enforcer/out

ENV ENFORCER_ROOT="/app/enforcer"
