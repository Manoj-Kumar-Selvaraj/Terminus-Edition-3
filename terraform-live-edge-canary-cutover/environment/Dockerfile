# Go is the primary language of the live edge control plane; Terraform is a
# pinned static binary layered on the same bookworm image so apply can compile
# edgectl and drive the local providers offline.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="terraform-live-edge-canary-cutover" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.created="2026-08-02T00:00:00Z"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    CHECKPOINT_DISABLE=1 \
    TF_IN_AUTOMATION=1 \
    TF_CLI_CONFIG_FILE=/app/environment/terraform.tfrc \
    GOTOOLCHAIN=local

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        jq \
        python3 \
        tmux \
        unzip \
    && rm -rf /var/lib/apt/lists/*

ARG TERRAFORM_VERSION=1.9.8
ARG TERRAFORM_SHA256=186e0145f5e5f2eb97cbd785bc78f21bae4ef15119349f6ad4fa535b83b10df8
RUN curl -fsSL -o /tmp/terraform.zip \
        "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    && echo "${TERRAFORM_SHA256}  /tmp/terraform.zip" | sha256sum -c - \
    && unzip -q /tmp/terraform.zip -d /usr/local/bin \
    && rm -f /tmp/terraform.zip \
    && chmod 0755 /usr/local/bin/terraform \
    && terraform version

COPY mirror/providers.tf /opt/terraform-mirror-src/providers.tf
RUN mkdir -p /opt/terraform-provider-mirror \
    && cd /opt/terraform-mirror-src \
    && terraform providers mirror -platform=linux_amd64 /opt/terraform-provider-mirror \
    && rm -rf /opt/terraform-mirror-src

WORKDIR /app

COPY terraform.tfrc /app/environment/terraform.tfrc
COPY bin/edgectl-put /app/bin/edgectl-put
COPY bin/edge-cutover-apply /app/bin/edge-cutover-apply
COPY docs/ /app/environment/docs/
COPY edgectl/ /app/environment/edgectl/
COPY terraform/ /app/environment/terraform/

RUN chmod 0755 /app/bin/edgectl-put /app/bin/edge-cutover-apply \
    && chmod -R go-w /app/environment /app/bin \
    && mkdir -p /app/var/edge \
    && cd /app/environment/edgectl && go build -o /tmp/edgectl-warm ./cmd/edgectl \
    && rm -f /tmp/edgectl-warm

CMD ["/bin/bash", "-l"]
