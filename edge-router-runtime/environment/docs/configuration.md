# Configuration and discovery contract

The process consumes complete desired-state JSON. The bootstrap file in the image is `/app/edge-router/config.json`.

## Desired-state document

Top-level fields:

- `schema_version`: integer, currently `1`.
- `routes`: array of route objects.
- `pools`: array of upstream-pool objects.
- `source_revisions`: map of source name to accepted integer revision.
- `source_digests`: map of source name to accepted content digest.

A route has a stable `id`, a `match` object, a referenced `pool_id`, and optional integer `priority`. Route match fields are `host`, `path_prefix`, and an optional method list. Hosts are compared case-insensitively. Path prefixes are normalized to begin with `/`. Methods are normalized to uppercase.

A pool has a stable `id`, an endpoint list, selection policy, retry policy, optional failover pool IDs, health policy, drain policy, and optional metadata.

Endpoint fields are `address`, positive integer `weight`, optional `transport`, and optional metadata. Addresses use host:port form. The runtime treats equivalent network identities as one logical endpoint identity when establishing continuity across generations.

## Selection policy

`selection.mode` identifies the pool algorithm. The starter configuration uses weighted selection. `sticky_header` may name a request header used as an affinity key. `affinity_ttl_seconds` bounds entry lifetime and `affinity_capacity` bounds per-pool affinity state.

## Retry and failover

`retry.max_attempts` is the total bounded attempt count for a request. `retry_status` may identify HTTP statuses eligible for another attempt. Failover pool IDs belong to the same immutable serving generation as the route that references them.

A request must not repeatedly target an endpoint already attempted for that request. When no eligible primary or failover endpoint exists, the data plane returns service unavailable rather than forwarding to an ineligible member.

## Health and drain policy

Health configuration defines the probe path, interval, timeout, and transition thresholds. Health state is runtime state and is not serialized into route configuration.

Drain configuration defines a maximum drain duration. Removal from accepted membership prevents new assignments while already-owned request/connection work is allowed to complete within lifecycle limits.

## Source snapshots

The admin submission endpoints accept this shape:

```json
{
  "source": "provider-a",
  "revision": 42,
  "routes": [],
  "pools": [],
  "observed_at": "2026-08-18T00:00:00Z"
}
```

Each source snapshot is complete for that source. Revisions are ordered independently per source. The same source revision with identical semantic content is a duplicate. The same source revision with different semantic content is a conflict. Older revisions are stale. None of those outcomes represent a newly accepted desired generation.

Accepted source material is merged deterministically by source identity before validation and compilation. A rejected candidate does not replace the last accepted material for that source.

## Validation

Validation rejects at least these classes of input:

- unsupported schema version;
- missing routes or pools;
- duplicate route or pool IDs;
- references to absent pools;
- invalid retry or drain bounds;
- missing endpoint addresses;
- non-positive or excessive endpoint weights;
- duplicate canonical endpoint identities within a pool;
- malformed endpoint addresses.

Validation and compilation operate on a complete candidate. Serving state changes only after the candidate has passed the full configuration contract.
