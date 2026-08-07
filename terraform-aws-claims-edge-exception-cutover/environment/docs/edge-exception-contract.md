# Claims edge exception cutover contract

The platform serves three logical edges from one reusable module: the main
static/API edge, a failover static edge, and a signed-content edge. Inputs are
JSON under `/app/data`. Outputs the workspace must expose after plan are
`distribution_ids`, `origin_access_control_ids`, `web_acl_arns`, `bucket_names`,
and `signed_path_patterns`.

## Behaviors the lab enforces

Path rules are matched by ascending `priority` (lower wins). Each rule selects
an `origin_id`, allowed methods, cache mode (`no-cache` vs cacheable), and
whether the path is signed. A default `/*` rule must not outrank more specific
API, maintenance, failover, or signed rules.

Custom auth headers configured on an origin apply only when that origin is
selected. Private object origins require an origin-access identity relation in
the plan; requests that reach them without that relation fail closed in the lab.

Signed access is allowed only for exception rows whose `status` is `approved`
and whose `expires_on` is still in the future relative to the lab clock. The
signed path must match the exception `path_pattern`. Neighboring unsigned paths
must not inherit trust.

Every distribution named in the WAF policy shares the same rate window and TLS
minimum. Security response headers (content-type options, frame deny, same-origin
referrer, HSTS) attach to served content. Standard logs use the logging policy
bucket host form `<bucket>.s3.amazonaws.com` with the listed prefixes.

Unsafe policy inputs must fail during `terraform plan` before the lab mutates
runtime state: public object-origin intent, weak TLS, missing WAF coverage for
a required edge, unknown signed exceptions, conflicting priorities, and logging
drift.

## Operator command

`/app/bin/edge-exception-cutover` plans the workspace at
`/app/terraform/workspaces/edge`, writes `/app/var/edge/plan.json`, starts local
origin stubs and the edge proxy, runs the probe battery, and writes
`/app/var/edge/cutover-evidence.json`. The evidence object includes
`status`, `plan_digest`, `probe_results`, `cache_events`, `rate_events`, and
`evidence_digest`. `status` is `READY` only when all contracted probes pass.
