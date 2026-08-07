# Canonical Python base; the verifier is a pure pytest suite over the rendered
# Terraform plan document, so no Terraform toolchain is needed here.
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir \
        pytest==8.3.5 \
        pytest-json-ctrf==0.5.3

# Parent directories for every artifact declared in task.toml.
RUN mkdir -p /app/output /app/environment/terraform/modules/eks_weekend_fleet /logs/verifier /tests

# Separate-verifier mode skips host upload of tests/; bake them into the image.
COPY test.sh conftest.py /tests/
COPY test_*.py /tests/
COPY fixtures/ /tests/fixtures/
RUN chmod 0755 /tests/test.sh

WORKDIR /app
