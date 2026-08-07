# Fleet weekend harden — posture contract

Binding contract for the Ansible under `/app/environment/ansible` and for the
live trees it leaves on disk. `/app/bin/fleet-harden-apply` is the only supported
entry point. The instruction states the recovery goal; anything about layouts,
ports, listener bodies, config line shapes, scrape wiring and the seal document
is defined here.

We run three logical edges on one control host. Paths below are absolute.

## 1. Edge map

| Inventory host | On-disk root | Role label | Metrics | Audit bridge | Promtail | Falco |
|----------------|--------------|------------|---------|--------------|----------|-------|
| edge-app | `/app/edges/app` | `app` | 9100 | 7375 | 9080 | 8765 |
| edge-data | `/app/edges/data` | `data` | 9110 | 7385 | 9090 | 8775 |
| edge-ops | `/app/edges/ops` | `ops` | 9120 | 7395 | 9105 | 8785 |

Control-plane state for scrape targets and the seal lives under
`/app/var/fleet-harden`. Role labels in host_vars, `inventory.json`, metrics
series and scrape targets must agree for each edge. Ports above are the only
ports those adapters may bind.

## 2. Ordered stages

Hardening is staged. Each edge writes markers at
`<root>/var/lib/fleet-harden/stage-NN.ok` for `NN` = `01` … `09`. The control
host writes `/app/var/fleet-harden/stage-10.ok` and
`/app/var/fleet-harden/stage-11.ok`.

A stage may create its marker only after the previous marker on that same root
exists. Soft-skipping predecessor checks is a contract failure even when later
markers appear. Stage 10 may run only after every edge has `stage-09.ok`. Stage
11 may run only after `stage-10.ok`.

| Marker | Role | What it seals |
|--------|------|---------------|
| 01 | inventory_probe | `<root>/var/lib/fleet-harden/inventory.json` with hostname, role, the four ports from §1, and `chain_token` from §4 |
| 02 | baseline_packages | required packages present; `packages.seal` matches §3.1 |
| 03 | patch_window | authoritative patch stamp installed (see §3) |
| 04 | auditd_bridge | audit health listener up with live `chain_token` |
| 05 | node_metrics | metrics exporter up with the correct `fleet_role` label |
| 06 | log_ship | promtail config written; ready listener pulls audit token live |
| 07 | runtime_sensor | falco rules written; health listener exposes the observability wire |
| 08 | host_firewall | metrics allow/deny policy file written |
| 09 | ssh_posture | sshd hardening snippet written |
| 10 | scrape_mesh | control scrape targets derived from live edges |
| 11 | posture_seal | posture report published |

## 3. Patch evidence

Authoritative stamp: `/app/environment/evidence/patch-stamp.txt`.

`/app/environment/evidence/decoy-stamp.txt` is not authoritative and must not be
installed on any edge.

`/app/environment/evidence/audit-findings.json` carries the engagement control
list under `required_controls`. The sealed posture report must echo that list
verbatim.

On every edge the installed stamp file is `<root>/etc/fleet-harden/patch-stamp`.
Contents must match the authoritative stamp file after trimming trailing
whitespace. A trailing newline on the installed file is fine.

### 3.1 Package seal

`<root>/var/lib/fleet-harden/packages.seal` is a JSON array of the exact set:

```
["ca-certificates","curl","procps","python3"]
```

Order in the file may vary; the sorted set must equal the array above. A seal
that merely looks present while omitting required packages fails the contract.

## 4. Adapter listeners and observability chain

Every adapter binds `127.0.0.1` on the port from §1 for that edge.

`chain_token` is the first 16 lowercase hex characters of the SHA-256 digest of
the UTF-8 string:

```
{hostname}|{role}|{audit_port}|{metrics_port}|{promtail_port}|{falco_port}
```

using the inventory hostname and §1 role/ports for that edge. Inventory must
store that value under `chain_token`.

Audit bridge (`/healthz`): JSON body must include `"component":"auditd"` and the
live `chain_token` from inventory.

Node metrics (`/metrics`): Prometheus text exposition must include a sample

```
fleet_node_up{fleet_role="<role>"} 1
```

where `<role>` is that edge’s role from §1 (`app`, `data`, or `ops`).

Promtail ready (`/ready`): JSON body must include that edge’s audit bridge port
as a decimal string **and** `"audit_token"` equal to the `chain_token` currently
served by the local audit `/healthz`. A static ready body that never contacts
audit fails the chain even if the audit port digit appears in the JSON.

Falco health (`/healthz`): JSON body must include that edge’s metrics port and
promtail port as decimal strings, and a `wire` string that contains the live
audit token (the same value promtail’s `audit_token` carries) plus those ports.
Serving only a metrics port digit is not enough.

## 5. Config files that must agree

These files sit under each edge root. Values for `<metrics_port>`,
`<audit_port>` and `<promtail_port>` are taken from §1 for that edge.

Promtail — `<root>/etc/fleet-harden/promtail.yml` — must contain:

```
loki: http://loki.fleet.internal:3100
audit_bridge: 127.0.0.1:<audit_port>
metrics_port: <metrics_port>
```

Falco rules — `<root>/etc/fleet-harden/falco-rules.yml` — must contain lines for
`metrics_port`, `audit_port` and `promtail_port` set to that edge’s ports.

Firewall policy — `<root>/etc/fleet-harden/nft.allow` — must be exactly these
two lines (trailing newline allowed):

```
allow tcp <metrics_port> from 172.28.0.0/16
deny tcp <metrics_port> from 0.0.0.0/0
```

An allow from `0.0.0.0/0` is a contract failure even if metrics still scrape
locally.

SSH snippet — `<root>/etc/fleet-harden/sshd_snippet` — must contain exactly:

```
PasswordAuthentication no
PermitRootLogin no
MaxAuthTries 3
```

`PasswordAuthentication yes` is not acceptable.

## 6. Scrape mesh

`/app/var/fleet-harden/scrape/targets.json` is a JSON array of three objects in
inventory order `[edge-app, edge-data, edge-ops]`. Each object has:

| Field | Type | Rule |
|-------|------|------|
| `host` | string | inventory hostname |
| `port` | integer | that edge’s live metrics port from §1 |
| `fleet_role` | string | same role as that edge’s `inventory.json`, which must match §1 |
| `chain_token` | string | same `chain_token` as that edge’s `inventory.json` |

Hardcoding role labels or reordering hosts so the array is not app→data→ops
fails the contract even when the JSON looks tidy.

## 7. Posture report

`/app/var/fleet-harden/posture-report.json` is a single JSON object:

| Field | Type | Rule |
|-------|------|------|
| `status` | string | must be `ok` |
| `patch_stamp` | string | trimmed contents of the authoritative stamp file |
| `scrape_cidr` | string | must be `172.28.0.0/16` |
| `edges` | array | must be `["edge-app", "edge-data", "edge-ops"]` |
| `scrape_targets` | array | must equal the parsed contents of `scrape/targets.json` |
| `required_controls` | array | must equal `required_controls` from `audit-findings.json` |
| `checks` | object | keys `inventory`, `packages`, `packages_seal`, `patch`, `auditd`, `metrics`, `promtail`, `falco`, `firewall`, `ssh`, `scrape`, `chain`, `idempotent` — each a JSON boolean `true` |

## 8. Apply and re-apply

`/app/bin/fleet-harden-apply` runs the site play for `/app/environment/ansible`,
leaves the adapters listening, and writes the posture report. A second apply on
the same host must succeed and leave the same contract-satisfying live state.
