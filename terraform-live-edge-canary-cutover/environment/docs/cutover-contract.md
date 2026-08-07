# Live edge canary cutover — control contract

This document is binding for Terraform under `/app/environment/terraform`, the
live edge control plane started by `/app/bin/edge-cutover-apply`, and the seal
written at `/app/var/edge/cutover-seal.json`. The instruction states the weekend
goal; layouts, API shapes, phase order and safety gates are defined here.

The control plane listens on `127.0.0.1:8787` and persists under
`/app/var/edge/state`. Synthetic traffic runs for the whole apply window.
Terraform must drive the live API into a contract-satisfying posture without
breaching the error budget while canary weight is raised.

## 1. Inventory

Authoritative inventory: `/app/environment/terraform/inventory/edge-fleet.auto.tfvars.json`.

It declares the engagement id, hostname, scrape/error budget, networks, blue and
green origin pools, WAF policy, TLS material, canary route id, DNS zone/name,
and observatory probes. Do not invent alternate ids; compose from this file and
the naming rules below.

## 2. Live API (normative)

Base URL: `http://127.0.0.1:8787`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/healthz` | liveness; body includes `status`=`ok` |
| GET | `/v1/snapshot` | full durable state |
| GET | `/v1/metrics` | live traffic counters |
| PUT | `/v1/networks/{id}` | declare a network fabric |
| PUT | `/v1/pools/{id}` | declare an origin pool on a ready network |
| PUT | `/v1/canary/{id}` | set green canary weight for a route |
| PUT | `/v1/waf/{id}` | install WAF policy |
| PUT | `/v1/tls/{id}` | install TLS material for a hostname |
| PUT | `/v1/dns/{zone}/{name}` | cut DNS to a pool |

Conflict responses use HTTP 409 and `{"error":"<reason>"}`.

### Networks

Body:

```json
{"id":"<id>","cidr":"<cidr>","region":"<region>","status":"ready"}
```

`status` must be `ready` before any pool may reference the network.

### Pools

Body:

```json
{
  "id": "<id>",
  "network_id": "<network id>",
  "color": "blue|green",
  "min_healthy": <int>,
  "origins": [{"id":"<id>","host":"<host>","port":<int>,"healthy":true}]
}
```

A pool is healthy when the count of `healthy` origins is >= `min_healthy` and
the referenced network is `ready`. Blue and green colours must not share a pool
id.

### Canary

Body:

```json
{
  "id": "<route id>",
  "blue_pool": "<id>",
  "green_pool": "<id>",
  "weight_green": <0-100>
}
```

Rules enforced by the control plane:

- `weight_green` may move above 0 only when both pools are healthy.
- Weight may only move along the inventory `canary_steps` sequence (no skipping).
- While `weight_green` > 0, `GET /v1/metrics` `error_rate_pct` must stay
  `<= inventory.error_budget_pct` or further increases are rejected.

### WAF

Body:

```json
{
  "id": "<id>",
  "mode": "detect|enforce",
  "rules": [{"id":"<id>","action":"block|allow","match":"<expr>"}]
}
```

DNS cutover to green requires `mode`=`enforce` and every inventory rule present
by id. `detect` is insufficient for cutover.

### TLS

Body:

```json
{"id":"<id>","hostname":"<hostname>","fingerprint":"<hex>"}
```

Hostname must equal inventory `edge_hostname`. Fingerprint must equal inventory
`tls_fingerprint`.

### DNS cutover

Body:

```json
{
  "zone": "<zone>",
  "name": "<name>",
  "target_pool": "<pool id>",
  "require_canary_weight": 100,
  "require_waf_enforce": true
}
```

The control plane rejects the call unless all of the following hold:

- canary `weight_green` is exactly 100
- WAF mode is `enforce`
- `target_pool` is the green pool and that pool is healthy
- TLS material exists for inventory `edge_hostname`

Cutting DNS to green before canary completion is a contract failure even if the
PUT is attempted.

## 3. Terraform layout

Root module: `/app/environment/terraform`.

Required child modules (under `modules/`):

| Module | Responsibility |
|--------|----------------|
| `network_fabric` | PUT every inventory network to ready |
| `origin_pool` | PUT blue and green pools with all origins |
| `waf_policy` | PUT WAF with inventory rules, final mode enforce |
| `tls_material` | PUT TLS for the edge hostname |
| `canary_route` | walk `canary_steps` in order against the live API |
| `dns_cutover` | PUT DNS only after canary 100 + WAF enforce |
| `observatory` | record probe specs under `/app/var/edge/observatory` |
| `traffic_guard` | assert live metrics within budget after DNS cutover |

Root must wire modules with explicit dependencies:

networks → pools → (waf ∥ tls) → canary steps → dns → observatory → traffic_guard.

Providers may be `local`, `null`, and `external` only (no cloud credentials).
Live mutation happens through `/app/bin/edgectl-put` invoked from Terraform
provisioners or external data sources.

## 4. Apply entrypoint

`/app/bin/edge-cutover-apply` must:

1. Ensure `/app/var/edge` exists.
2. Build and start `edgectl` from `/app/environment/edgectl` if not healthy.
3. Run Terraform init/apply for `/app/environment/terraform` against local state
   under `/app/var/edge/terraform`.
4. Leave the control plane running.
5. Write `/app/var/edge/cutover-seal.json`.
6. Write `/app/var/edge/snapshot.json` as the JSON body of `GET /v1/snapshot`
   at seal time (same durable state the control plane would return).

A second apply must succeed and keep the seal contract-true (idempotent).

## 5. Cutover seal

`/app/var/edge/cutover-seal.json` object:

| Field | Rule |
|-------|------|
| `status` | `"ok"` |
| `engagement` | inventory `engagement` |
| `hostname` | inventory `edge_hostname` |
| `canary_weight_green` | integer `100` |
| `dns_target_pool` | green pool id |
| `waf_mode` | `"enforce"` |
| `error_rate_pct` | number `<= inventory.error_budget_pct` |
| `networks_ready` | integer count of ready networks |
| `blue_healthy` | boolean `true` |
| `green_healthy` | boolean `true` |
| `tls_fingerprint` | inventory fingerprint |
| `steps_applied` | array equal to inventory `canary_steps` |

## 5.1 Snapshot artifact

`/app/var/edge/snapshot.json` is the durable control-plane snapshot taken when
the seal is written. It must match `GET /v1/snapshot` field layout from §2 and
agree with the seal on:

- canary `weight_green` for inventory `canary_route_id` equals `100`
- WAF `mode` for inventory WAF id equals `enforce`
- TLS `fingerprint` and `hostname` for inventory TLS id
- DNS record for inventory zone/name with `target_pool` equal to the green pool id

## 6. Safety

Synthetic traffic is part of the problem. Raising canary weight while injecting
faulty green origins, skipping steps, enforcing WAF late, or flipping DNS early
must fail closed at the API or at `traffic_guard`. Matching a pretty seal without
live metrics within budget is not sufficient.
