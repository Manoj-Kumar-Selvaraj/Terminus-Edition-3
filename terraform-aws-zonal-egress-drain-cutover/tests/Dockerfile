FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="terraform-aws-zonal-egress-drain-cutover-tests" \
      org.opencontainers.image.version="1.0.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    CHECKPOINT_DISABLE=1 \
    TF_IN_AUTOMATION=1 \
    TF_CLI_CONFIG_FILE=/app/terraform.tfrc \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

ARG TERRAFORM_VERSION=1.9.8
ARG TERRAFORM_SHA256=186e0145f5e5f2eb97cbd785bc78f21bae4ef15119349f6ad4fa535b83b10df8
RUN curl -fsSL -o /tmp/terraform.zip \
        "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    && echo "${TERRAFORM_SHA256}  /tmp/terraform.zip" | sha256sum -c - \
    && unzip -q /tmp/terraform.zip -d /usr/local/bin \
    && rm -f /tmp/terraform.zip \
    && chmod 0755 /usr/local/bin/terraform

RUN pip install --no-cache-dir \
        pytest==8.3.5 \
        pytest-json-ctrf==0.5.3 \
        ruff==0.8.4

WORKDIR /app

COPY fixtures/mirror/providers.tf /opt/terraform-mirror-src/providers.tf
RUN mkdir -p /opt/terraform-provider-mirror \
    && cd /opt/terraform-mirror-src \
    && terraform providers mirror -platform=linux_amd64 /opt/terraform-provider-mirror \
    && rm -rf /opt/terraform-mirror-src

COPY terraform.tfrc /app/terraform.tfrc

RUN mkdir -p /app/terraform /app/var/egress /app/output /tests

COPY test.sh /tests/test.sh
COPY test_outputs.py /tests/test_outputs.py
COPY fixtures/ /tests/fixtures/

RUN chmod +x /tests/test.sh

WORKDIR /tests
