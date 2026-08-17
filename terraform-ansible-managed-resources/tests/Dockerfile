FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="terraform-ansible-managed-resources-verifier" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="MIT"

ARG TERRAFORM_VERSION=1.10.5
ARG TERRAFORM_SHA256=0566a24f5332098b15716ebc394be503f4094acba5ba529bf5eb0698ed5e2a90

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOTOOLCHAIN=local \
    ANSIBLE_NOCOLOR=1 \
    ANSIBLE_HOST_KEY_CHECKING=False \
    ANSIBLE_CONFIG=/app/provider/config/ansible.cfg \
    TF_CLI_CONFIG_FILE=/tmp/terraform.rc

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ansible-core \
        bash \
        ca-certificates \
        cron \
        curl \
        jq \
        passwd \
        procps \
        python3 \
        python3-pip \
        sudo \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSLo /tmp/terraform.zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    && echo "${TERRAFORM_SHA256}  /tmp/terraform.zip" | sha256sum -c - \
    && unzip -q /tmp/terraform.zip -d /usr/local/bin \
    && rm -f /tmp/terraform.zip \
    && terraform version

RUN python3 -m pip install --no-cache-dir --break-system-packages \
      pytest==8.4.1 \
      pytest-json-ctrf==0.3.5 \
    && python3 -c "import pytest; print('pytest', pytest.__version__)"

RUN mkdir -p /app/provider /opt/terraform/plugins/registry.terraform.io/local/ansibleops/0.1.0/linux_amd64
COPY . /tests/
RUN chmod 0755 /tests/test.sh
WORKDIR /app
