FROM golang:1.24-bookworm AS build
WORKDIR /src
COPY . .
RUN go build -o /out/routecp ./cmd/routecp

FROM golang:1.24-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -r -u 10001 routecp \
    && mkdir -p /app/routecp/state /app/routecp/config \
    && chown -R routecp:routecp /app/routecp
COPY --from=build --chown=routecp:routecp /src/ /app/routecp/
COPY --from=build /out/routecp /usr/local/bin/routecp
USER routecp
WORKDIR /app/routecp
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/routecp"]
