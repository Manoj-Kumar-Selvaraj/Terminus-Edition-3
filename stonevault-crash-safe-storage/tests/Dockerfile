FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.source="https://github.com/Manoj-Kumar-Selvaraj/Terminus-Edition-3" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.licenses="MIT"

RUN pip install --no-cache-dir \
    iniconfig==2.0.0 \
    packaging==24.2 \
    pluggy==1.5.0 \
    pygments==2.19.1 \
    pytest==8.3.5

RUN mkdir -p /app/stonevault /logs/verifier /tests
COPY test_outputs.py /tests/test_outputs.py
COPY test.sh /tests/test.sh
RUN chmod +x /tests/test.sh
WORKDIR /app/stonevault
