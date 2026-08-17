FROM public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36

LABEL org.opencontainers.image.source="https://github.com/Manoj-Kumar-Selvaraj/Terminus-Edition-3" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.licenses="MIT"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       asciinema \
       binutils \
       build-essential \
       ca-certificates \
       make \
       patch \
       tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/stonevault
COPY stonevault/Cargo.toml /app/stonevault/Cargo.toml
COPY stonevault/build.rs /app/stonevault/build.rs
COPY stonevault/Makefile /app/stonevault/Makefile
COPY stonevault/storage /app/stonevault/storage
COPY stonevault/src /app/stonevault/src
COPY stonevault/docs /app/stonevault/docs
RUN make

CMD ["bash"]
