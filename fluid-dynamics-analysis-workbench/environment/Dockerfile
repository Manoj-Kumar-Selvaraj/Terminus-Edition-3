FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

LABEL org.opencontainers.image.title="fluid-dynamics-analysis-workbench" \
      org.opencontainers.image.description="Deterministic fluid dynamics analysis workbench" \
      org.opencontainers.image.version="0.1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    FLUIDLAB_HOME=/app/fluidlab \
    PYTHONPATH=/app/fluidlab/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        bash \
        ca-certificates \
        tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/fluidlab
COPY fluidlab/ /app/fluidlab/
RUN /app/fluidlab/scripts/build.sh

CMD ["sleep", "infinity"]
