FROM public.ecr.aws/docker/library/maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e

LABEL org.opencontainers.image.source="local/jenkins-home-insights" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT"

RUN apt-get update \
    && apt-get install -y --no-install-recommends asciinema tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY plugin/pom.xml plugin/pom.xml
COPY plugin/bin plugin/bin
COPY plugin/config plugin/config
COPY plugin/src plugin/src
COPY plugin/docs plugin/docs
COPY plugin/README.md plugin/README.md

RUN chmod 0755 plugin/bin/build-core plugin/bin/insights \
    && sh plugin/bin/build-core \
    && sh plugin/bin/insights generate --home /var/lib/jenkins-sanitized --records 14536 \
    && sh plugin/bin/insights reconcile --home /var/lib/jenkins-sanitized --state /var/lib/insights

ENV JENKINS_HOME=/var/lib/jenkins-sanitized
ENV INSIGHTS_STATE=/var/lib/insights
CMD ["sleep", "infinity"]
