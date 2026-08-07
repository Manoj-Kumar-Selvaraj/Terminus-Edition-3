# VPC reconciliation controller contract

Implement `/app/bin/vpc-reconcile` from `/app/cmd/vpcreconcile`. Observed cloud
state is never read from files under `/app/seed` or `/app/evidence` by the
controller. Query and mutate only through the control-plane HTTP API at
`VPC_CONTROLPLANE_URL` (default `http://127.0.0.1:7432`). Desired intent is
always `/app/data/desired.json` relative to `--root`.

## Operator commands

```bash
vpc-reconcile inspect --root /app --json
vpc-reconcile plan --root /app --json
vpc-reconcile apply --root /app --owner OWNER [--fail-after STAGE]
vpc-reconcile resume --root /app --owner OWNER
vpc-reconcile verify --root /app --json
```

JSON output uses snake_case keys.

### inspect

Must include `feature_level` (integer >= 1) and `controlplane_reachable`
(boolean).

### plan

Read-only. Must not create or modify `/app/var/reconcile/state.db` (or any
SQLite files under that directory). Output must include:

- `schema_version`: exactly `vpc-reconcile.aws.1`
- `environment`: from desired config
- `config_digest`: stable digest of desired config used for fencing
- `route_tables`, `gateway_endpoints`, `subnets`, `moved`, `flow_log`,
  `resolver_security_group`, `drift_report`, `outputs`, `plan_actions`

### apply / resume

Persist durable progress in SQLite at `<root>/var/reconcile/state.db` with
WAL mode. On success write recovered state into that database and emit
journal rows with at least `event`, `owner`, and `config_digest`.

Supported `--fail-after` stages: `route_commit`, `endpoint_commit`. After the
durable stage is written, exit non-zero even if state was persisted. Resume
by the same owner must continue without duplicating routes, endpoint
associations, moved entries, or state-affecting journal events.

### verify

Read-only against existing SQLite state. Before a successful recovery it must
not report `phase: "READY"` or `valid: true`. After success: `valid: true`
and `phase: "READY"`.

## Control-plane API

| Method | Path | Role |
|--------|------|------|
| GET | `/health` | liveness |
| GET | `/v1/observed` | routes, endpoints, nat_health, imports, audit |
| POST | `/v1/routes/commit` | commit recovered route tables; returns `token` |
| POST | `/v1/endpoints/commit` | commit endpoint associations; returns `token` |
| GET | `/v1/committed` | currently committed cloud view |

Commit bodies must include `owner` and the recovered objects. Responses
include a non-empty `token` string that must be stored in the journal for
that stage. Replay of an identical commit with the same owner and digest is
idempotent at the control-plane.

## Routing and endpoints

- App tier `0.0.0.0/0` uses the healthy same-AZ NAT from control-plane NAT
  health (`state` equal to `available`). Missing same-AZ NAT fails with
  substring `missing nat gateway` before mutation.
- Data tier must not receive a default internet route.
- Preserve observed manual routes (`owner` equal to `manual`) on the matching
  tables and keep unknown metadata fields.
- Only `s3` and `dynamodb` gateway endpoints are supported; anything else
  fails with `unsupported` before mutation.
- Endpoint `route_table_ids` must equal `outputs.private_app_route_table_ids`
  (recovered app tables, including imported IDs). Policy
  `Statement[0].Condition.StringEquals["aws:PrincipalAccount"]` must equal
  the desired `account_id` or fail with `account mismatch`.

## CIDR identity and moves

- Overlapping subnet CIDRs fail with `overlaps`.
- Subnets outside `vpc_cidr` fail with `outside vpc_cidr`.
- Duplicate imported CIDRs fail with `ambiguous imported cidr`.
- Match imported subnet resources by CIDR; preserve imported subnet and route
  table IDs when present.
- Emit top-level `moved` entries shaped
  `{"action":"moved","from":"<legacy>","to":"<current app subnet address>"}`
  for legacy integer-indexed private subnet addresses. Each `from` appears at
  most once.

## Audit and drift

- `flow_log.subnet_ids` covers every recovered subnet ID.
- Preserve existing flow-log id/metadata when the destination account matches;
  destination account mismatch fails with `account mismatch`.
- Flow-log IAM policy is flat `{"Action":[...],"Resource":"<arn>"}` with
  non-empty `logs:` actions including `logs:CreateLogStream` and
  `logs:PutLogEvents`, no `logs:*`, and a non-wildcard log-group ARN ending
  in `:*`.
- Resolver ingress is exactly TCP/53 and UDP/53 from desired
  `resolver.allowed_cidrs` under key `cidr_blocks`.
- Manual resolver rules from observed audit appear in `drift_report` as
  `report_only` entries and are not deleted.

## Journal fencing

- Interior journal corruption (bad checksum or unreadable row before the
  newest row) fails with `journal corruption`.
- A torn/incomplete newest journal row may be truncated on resume.
- Different owner fails with `stale owner`.
- Changed config digest fails with `config digest changed`.
- Successful repeated `apply` is a no-op for recovered state and does not
  append duplicate state-affecting journal events.

## Public run artifact

`/app/bin/vpc-reconcile-run` regenerates Terraform plan JSON at
`/app/var/reconcile/plan.json`, runs the controller to READY, and writes
`/app/output/reconciliation-report.json`:

```json
{
  "schema_version": "vpc-reconcile-report.1",
  "status": "READY",
  "config_digest": "<hex>",
  "plan_digest": "<hex>",
  "state_digest": "<hex>",
  "controlplane_token_route": "<token>",
  "controlplane_token_endpoint": "<token>",
  "report_digest": "<hex>",
  "outputs": {"private_app_route_table_ids": ["..."]}
}
```

`report_digest` hashes the report fields excluding itself. A second identical
run must keep the same `report_digest`.
