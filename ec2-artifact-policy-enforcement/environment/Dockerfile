FROM rust:1.85-slim-bookworm

LABEL org.opencontainers.image.title="PolicyGuard artifact enforcement lab"
LABEL org.opencontainers.image.version="1.0"

RUN apt-get update \
 && apt-get install -y --no-install-recommends bash ca-certificates openssl procps \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/policyguard
COPY policyguard/ /app/policyguard/
RUN cargo build --release \
 && chmod +x /app/policyguard/bin/* \
 && mkdir -p /app/policyguard/state

ENV POLICYGUARD_ROOT="/app/policyguard"
ENV PATH="/app/policyguard/bin:/app/policyguard/target/release:${PATH}"
