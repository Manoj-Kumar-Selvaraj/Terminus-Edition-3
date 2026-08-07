FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac AS runtime_build

WORKDIR /build
COPY fixtures/go.mod /build/go.mod
COPY fixtures/runtime/main.go /build/main.go
RUN go build -o /out/settlement-runtime . \
    && sha256sum /out/settlement-runtime > /out/settlement-runtime.sha256

FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="terraform-aws-lambda-settlement-dual-run-cutover-tests" \
      org.opencontainers.image.version="1.0.0"

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
        ca-certificates \
        curl \
        python3 \
        python3-pip \
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

RUN pip3 install --no-cache-dir --break-system-packages \
        pytest==8.3.5 \
        pytest-json-ctrf==0.5.3 \
        ruff==0.8.4

COPY fixtures/mirror/providers.tf /opt/terraform-mirror-src/providers.tf
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
RUN mkdir -p /app/cmd /app/internal /app/terraform /app/var/settlement /app/output /app/bin /app/data /app/config /tests

COPY test.sh /tests/test.sh
COPY test_outputs.py /tests/test_outputs.py
COPY fixtures/ /tests/fixtures/
COPY fixtures/bin/settlement-dual-run /app/bin/settlement-dual-run

RUN chmod +x /tests/test.sh /app/bin/settlement-dual-run

WORKDIR /tests
