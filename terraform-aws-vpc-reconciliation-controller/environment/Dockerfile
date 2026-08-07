# Multi-stage: Go toolchain from canonical golang image; Python final runtime.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS gotoolchain

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="terraform-aws-vpc-reconciliation-controller" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/anonymous/terminus-edition-3" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    CHECKPOINT_DISABLE=1 \
    TF_IN_AUTOMATION=1 \
    TF_CLI_CONFIG_FILE=/app/terraform.tfrc \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CGO_ENABLED=0 \
    PATH=/usr/local/go/bin:/usr/local/bin:/usr/bin:${PATH} \
    GOPATH=/go \
    GOCACHE=/tmp/go-cache

COPY --from=gotoolchain /usr/local/go /usr/local/go

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        gcc \
        libc6-dev \
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
    && chmod 0755 /usr/local/bin/terraform

COPY mirror/providers.tf /opt/terraform-mirror-src/providers.tf
RUN mkdir -p /opt/terraform-provider-mirror \
    && cd /opt/terraform-mirror-src \
    && terraform providers mirror -platform=linux_amd64 /opt/terraform-provider-mirror \
    && rm -rf /opt/terraform-mirror-src

WORKDIR /app

COPY go.mod /app/go.mod
COPY cmd/ /app/cmd/
RUN go mod tidy \
    && go build -o /app/bin/vpc-reconcile ./cmd/vpcreconcile \
    && test -f /go/pkg/mod/cache/download/modernc.org/sqlite/@v/v1.34.5.lock || true

COPY terraform.tfrc /app/terraform.tfrc
COPY docs/ /app/docs/
COPY data/ /app/data/
COPY evidence/ /app/evidence/
COPY seed/ /app/seed/
COPY controlplane/ /app/controlplane/
COPY terraform/ /app/terraform/
COPY bin/ /app/bin/

RUN mkdir -p /app/var/reconcile /app/output \
    && chmod +x /app/bin/vpc-controlplane /app/bin/vpc-reconcile-run \
    && chmod -R go-w /app/docs /app/data /app/evidence /app/seed /app/controlplane

CMD ["/bin/bash", "-l"]
