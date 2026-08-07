FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS mock-build
WORKDIR /src
COPY mock-azurerm/ ./
RUN go mod tidy \
    && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" \
       -o /out/terraform-provider-azurerm_v3.116.0

FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="terraform-azure-spoke-private-endpoint-transition" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/anonymous/terminus-edition-3" \
      org.opencontainers.image.licenses="Apache-2.0"

# Offline mock azurerm provider: live Azure credentials are unavailable in the
# lab, so the digest-pinned agent image ships a schema-compatible mock binary
# under the filesystem provider mirror (see README).

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    CHECKPOINT_DISABLE=1 \
    TF_IN_AUTOMATION=1 \
    TF_CLI_CONFIG_FILE=/app/terraform.tfrc \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
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

RUN mkdir -p /opt/terraform-provider-mirror/registry.terraform.io/hashicorp/azurerm/3.116.0/linux_amd64
COPY --from=mock-build /out/terraform-provider-azurerm_v3.116.0 \
    /opt/terraform-provider-mirror/registry.terraform.io/hashicorp/azurerm/3.116.0/linux_amd64/terraform-provider-azurerm_v3.116.0

WORKDIR /app

COPY terraform.tfrc /app/terraform.tfrc
COPY docs/ /app/docs/
COPY data/ /app/data/
COPY evidence/ /app/evidence/
COPY spoke_lab/ /app/spoke_lab/
COPY terraform/ /app/terraform/
COPY bin/ /app/bin/

RUN mkdir -p /app/var/spoke /app/output \
    && chmod +x /app/bin/spoke-pe-transition \
    && chmod -R go-w /app/docs /app/data /app/evidence /app/spoke_lab

CMD ["/bin/bash", "-l"]
