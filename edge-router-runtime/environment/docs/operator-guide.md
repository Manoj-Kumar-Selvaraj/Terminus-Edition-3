# Operator guide

## Validate configuration

```bash
edge-router-runtime validate --config /app/edge-router/config.json
```

Validation parses, normalizes, checks cross-references and policy bounds, then compiles a candidate graph without starting listeners.

## Start the runtime

```bash
edge-router-runtime serve \
  --config /app/edge-router/config.json \
  --state-dir /var/lib/edge-router \
  --listen 0.0.0.0:8080 \
  --admin-listen 127.0.0.1:9901
```

The public listener serves routed application traffic. The admin listener is intended for local operator automation and configuration/discovery providers.

## Admin interfaces

- `GET /healthz` reports admin-process liveness.
- `GET /readyz` reports whether a complete serving generation is published.
- `GET /v1/status` reports generation, accepted source fences, runtime object counts, and telemetry cardinality.
- `GET /v1/runtime` reports endpoint lifecycle/health state for the serving generation.
- `GET /v1/health?limit=N` returns recent health observations.
- `GET /v1/drains?limit=N` returns current drains and recently retired endpoint state.
- `GET /v1/checkpoints` lists persisted generation bodies.
- `POST /v1/config/snapshot` submits a complete source snapshot.
- `POST /v1/discovery/snapshot` uses the same source-snapshot contract for discovery providers.
- `GET /metrics` exports Prometheus text format.

Example source update:

```bash
curl -sS -X POST http://127.0.0.1:9901/v1/discovery/snapshot \
  -H 'content-type: application/json' \
  --data-binary @/tmp/provider-a.json
```

The response includes the source, revision, generation when applicable, and an acceptance status such as accepted, duplicate, stale, conflict, or rejected.

## Readiness

A process is not ready merely because the admin listener exists. Public readiness requires a complete published serving generation. Recovery or bootstrap compilation must finish before traffic is considered ready.

## Restart

The state directory is part of the runtime's operational state. Preserve it across process restart when accepted-generation recovery is required.

On startup the process attempts durable recovery before falling back to the bootstrap configuration. Recovery never depends on the availability of an external configuration provider. Source revision fences recovered from durable state protect startup from replayed older provider snapshots.

## Shutdown

SIGINT or SIGTERM removes readiness, stops both HTTP servers, cancels background reconciliation/health/drain work, closes reusable upstream transports, and waits for owned goroutines within the shutdown budget.

For routine maintenance, send SIGTERM and allow the process to finish its graceful shutdown. Avoid deleting the state directory unless a deliberate bootstrap reset is intended.

## Troubleshooting workflow

1. Check `/healthz` and `/readyz` separately.
2. Inspect `/v1/status` for serving generation and accepted source revisions.
3. Inspect `/v1/health` for endpoint observations.
4. Inspect `/v1/drains` for membership lifecycle state.
5. Inspect `/v1/checkpoints` if restart/recovery behavior is involved.
6. Review `/metrics` for update, request, health, retry, affinity, drain, and cardinality signals.

Configuration failures should be corrected at the source snapshot and resubmitted as a new valid revision. A rejected update does not require restarting the process.
