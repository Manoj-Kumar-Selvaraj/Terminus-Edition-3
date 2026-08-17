FROM public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac

LABEL org.opencontainers.image.title="terraform-ansible-managed-resources" \
      org.opencontainers.image.description="Inherited Terraform provider for Ansible-backed managed OS resources." \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.licenses="MIT"

ARG TERRAFORM_VERSION=1.10.5
ARG TERRAFORM_SHA256=0566a24f5332098b15716ebc394be503f4094acba5ba529bf5eb0698ed5e2a90

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    GOPROXY=https://proxy.golang.org,direct \
    GOTOOLCHAIN=local \
    ANSIBLE_NOCOLOR=1 \
    ANSIBLE_HOST_KEY_CHECKING=False \
    TF_CLI_CONFIG_FILE=/app/provider/config/terraform.rc \
    ANSIBLE_CONFIG=/app/provider/config/ansible.cfg \
    ANSIBLEOPS_ROOT=/app/provider

WORKDIR /app/provider

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ansible-core \
        asciinema \
        bash \
        ca-certificates \
        cron \
        curl \
        git \
        jq \
        passwd \
        procps \
        sudo \
        tmux \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSLo /tmp/terraform.zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    && echo "${TERRAFORM_SHA256}  /tmp/terraform.zip" | sha256sum -c - \
    && unzip -q /tmp/terraform.zip -d /usr/local/bin \
    && rm -f /tmp/terraform.zip \
    && terraform version

COPY ansibleops/ /app/provider/

RUN chmod 0755 /app/provider/scripts/*.sh \
    && mkdir -p /tmp/ansibleops /opt/terraform/plugins/registry.terraform.io/local/ansibleops/0.1.0/linux_amd64 \
    && go mod tidy \
    && go mod verify \
    && go mod vendor \
    && test -s /app/provider/go.sum \
    && test -d /app/provider/vendor \
    && /app/provider/scripts/build-provider.sh \
    && ansible-playbook --version \
    && terraform version

WORKDIR /app/provider
