FROM public.ecr.aws/docker/library/golang:1.24-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOTOOLCHAIN=local

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates nodejs node-typescript python3 python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --break-system-packages --no-cache-dir pytest==8.4.1 ansible-core==2.18.7

RUN mkdir -p /app/routecp /logs/verifier /tests
COPY . /tests/
RUN chmod 0755 /tests/test.sh
WORKDIR /app
