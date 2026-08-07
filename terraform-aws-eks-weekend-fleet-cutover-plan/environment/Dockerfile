# Canonical Python base: the plan renderer and the JSON well-formedness gate in
# /app/environment/scripts/render-eks-weekend-plan are Python, and Terraform is
# a single static binary layered on top.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="terraform-aws-eks-weekend-fleet-cutover-plan" \
      org.opencontainers.image.description="Offline Terraform plan workspace for an EKS weekend fleet control plane." \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive \
    TF_CLI_CONFIG_FILE=/app/environment/terraform.tfrc \
    CHECKPOINT_DISABLE=1 \
    TF_IN_AUTOMATION=1 \
    PATH="/app/environment/scripts:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        git \
        jq \
        less \
        tmux \
        unzip \
        vim-tiny \
    && rm -rf /var/lib/apt/lists/*

# Terraform is pinned by version and verified against the published checksum.
ARG TERRAFORM_VERSION=1.9.8
ARG TERRAFORM_SHA256=186e0145f5e5f2eb97cbd785bc78f21bae4ef15119349f6ad4fa535b83b10df8
RUN curl -fsSL -o /tmp/terraform.zip \
        "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    && echo "${TERRAFORM_SHA256}  /tmp/terraform.zip" | sha256sum -c - \
    && unzip -q /tmp/terraform.zip -d /usr/local/bin \
    && rm -f /tmp/terraform.zip \
    && chmod 0755 /usr/local/bin/terraform \
    && terraform version

# Vendor every provider package into an on-disk mirror so the workspace can be
# initialised with the network switched off.
COPY mirror/providers.tf /opt/terraform-mirror-src/providers.tf
RUN mkdir -p /opt/terraform-provider-mirror \
    && cd /opt/terraform-mirror-src \
    && terraform providers mirror -platform=linux_amd64 /opt/terraform-provider-mirror \
    && rm -rf /opt/terraform-mirror-src

WORKDIR /app

COPY terraform.tfrc /app/environment/terraform.tfrc
COPY scripts/ /app/environment/scripts/
RUN chmod 0755 /app/environment/scripts/render-eks-weekend-plan \
               /app/environment/scripts/simulate-eks-weekend-cutover

COPY terraform/ /app/environment/terraform/

RUN mkdir -p /app/output

CMD ["/bin/bash", "-l"]
