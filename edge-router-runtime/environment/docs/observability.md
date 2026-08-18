# Observability contract

The admin plane exposes process state as JSON and metrics as Prometheus text. Observability state has explicit owners so repeated configuration generations and endpoint churn remain bounded.

## Stable status fields

`GET /v1/status` includes:

- current reconciler generation;
- readiness;
- accepted source revision map;
- accepted source digest map;
- latest reconciliation event;
- serving generation when present;
- route and pool counts;
- active snapshot lease count;
- runtime pool and endpoint handle counts;
- telemetry series cardinality.

`GET /v1/runtime` reports serving-generation endpoint views with pool ID, endpoint identity, address, incarnation, membership state, health state, in-flight request count, and reusable connection count.

## Update telemetry

Configuration/discovery processing records the source, source revision, resulting runtime generation when applicable, outcome, and message. Operationally important outcomes are accepted, duplicate, stale, conflict, and rejected.

An accepted update is observable only after the serving generation has reached the publication/acceptance boundary. Rejected/stale/conflicting candidates do not appear as a new accepted generation.

## Request telemetry

Request metrics use stable route and pool identities rather than transient pointers. They distinguish successful upstream responses, route misses, and service-unavailable outcomes. Generation ownership allows metrics for retired generations to be removed when their owner is no longer reachable.

Retry telemetry should distinguish attempt number and outcome without using unbounded request identifiers as labels. Affinity telemetry should report bounded lookup hit/miss/stale-replacement behavior without exporting affinity keys.

## Endpoint telemetry

Health observations include pool, stable endpoint identity, address, resulting health state, response status, latency, error summary, and observation time. Recent observations are kept in a bounded history.

Drain status exposes membership state, incarnation, in-flight requests, reusable connection references, and deadline. Recently retired state is bounded and intended for operator diagnosis rather than permanent historical storage.

## Metric ownership

Metric owners are process, generation, pool-runtime, or endpoint-runtime lifecycle objects. A metric series must be removed when its lifecycle owner is retired and cannot be reached by a serving snapshot or active runtime operation.

Do not use raw source payloads, arbitrary URL paths, request IDs, client IPs, affinity keys, or error strings as metric labels. Those values create uncontrolled cardinality.

## Cardinality expectations

Under repeated valid updates with stable semantic topology, metric cardinality should converge instead of increasing with every runtime generation. Endpoint remove/re-add may legitimately create a new incarnation, but metrics for retired incarnations are eventually removed.

Affinity tables, observation history, retired-state history, and per-generation metric sets are all expected to have explicit bounds.

## Operator checks

Useful checks during a rolling membership change:

1. compare `/v1/status` serving generation with the update response generation;
2. confirm removed endpoints appear as draining rather than eligible for new work;
3. confirm health observations continue for endpoints that remain members;
4. confirm request failures do not select unhealthy or draining endpoints;
5. confirm retired endpoint/generation series disappear after lifecycle ownership ends;
6. confirm restart restores an accepted generation without a sudden cardinality reset followed by stale-series growth.
