# Final base is the canonical Go Bookworm image so agents can rebuild settlementctl
# from submitted controller sources while Terraform and the sealed runtime binary
# are baked at build time.
FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS runtime_build

WORKDIR /build
COPY cmd/runtime/go.mod /build/go.mod
COPY cmd/runtime/main.go /build/main.go
RUN go build -o /out/settlement-runtime . \
    && sha256sum /out/settlement-runtime > /out/settlement-runtime.sha256

FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="terraform-aws-lambda-settlement-dual-run-cutover" \
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
    GOTOOLCHAIN=local

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
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
    && chmod 0755 /usr/local/bin/terraform

COPY mirror/providers.tf /opt/terraform-mirror-src/providers.tf
RUN mkdir -p /opt/terraform-provider-mirror \
    && cd /opt/terraform-mirror-src \
    && terraform providers mirror -platform=linux_amd64 /opt/terraform-provider-mirror \
    && rm -rf /opt/terraform-mirror-src

COPY --from=runtime_build /out/settlement-runtime /opt/settlement-runtime
COPY --from=runtime_build /out/settlement-runtime.sha256 /opt/settlement-runtime.sha256
RUN chmod 0555 /opt/settlement-runtime \
    && /opt/settlement-runtime reset >/dev/null

WORKDIR /app
COPY terraform.tfrc /app/terraform.tfrc
COPY docs/ /app/docs/
COPY data/ /app/data/
COPY config/ /app/config/
COPY evidence/ /app/evidence/
COPY go.mod /app/go.mod
COPY internal/ /app/internal/
COPY cmd/settlementctl/ /app/cmd/settlementctl/
COPY terraform/ /app/terraform/
COPY bin/ /app/bin/

RUN mkdir -p /app/var/settlement /app/output \
    && chmod +x /app/bin/settlement-dual-run \
    && chmod -R go-w /app/docs /app/data /app/config /app/evidence

CMD ["/bin/bash", "-l"]
