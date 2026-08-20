FROM golang:1.24-bookworm AS build
WORKDIR /src
COPY . .
RUN go build -o /out/routecp ./cmd/routecp

FROM debian:bookworm-slim
RUN useradd -r -u 10001 routecp && mkdir -p /app/routecp/state /app/routecp/config && chown -R routecp:routecp /app/routecp
COPY --from=build /out/routecp /usr/local/bin/routecp
COPY config /app/routecp/config
USER routecp
WORKDIR /app/routecp
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/routecp"]
