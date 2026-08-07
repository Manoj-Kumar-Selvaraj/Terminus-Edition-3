# Zonal egress drain contract

Payments egress uses one public, one app, and one data subnet per AZ listed
in `/app/data/topology.json`. App workloads leave the VPC through the NAT
gateway that shares their AZ. Data subnets stay isolated: they must not
receive a module-owned IPv4 default route to the internet.

`/app/data/nat_health.json` and `/app/data/drain_policy.json` describe the
current drain window. New app flows may use a NAT only when that AZ is
`healthy`. A `draining` or `failed` NAT refuses new flows according to the
drain policy; traffic must not silently fall over to another AZ's NAT even
when that peer is healthy. Missing same-AZ NAT coverage for an enabled AZ is
a plan validation failure whose diagnostic mentions `same-AZ NAT`.

Gateway endpoints for services in `/app/data/services.json` attach to app
and data route tables and bypass NAT. Interface endpoints live only in app
subnets, keep private DNS enabled, and admit TCP 443 only from the app and
data CIDRs derived from topology. Resolver ingress is limited to TCP/UDP 53
from the corporate DNS CIDRs in topology. Do not use Terraform `data`
sources whose type starts with `aws_`; keep the plan credential-free with
`jsonencode` and input-derived ARNs. Account and region values come from
`/app/data/defaults.json`, not hardcoded literals that ignore inputs.

Legacy keys in `/app/data/legacy_addresses.json` must migrate with
per-AZ `moved` declarations from the former private subnet and private route
table addresses to the app subnet and app route table addresses for the same
keys. Unchanged identities must not be destroyed or replaced when planning
against that legacy continuity.

The public operator `/app/bin/zonal-egress-drain` plans the workspace under
`/app/terraform/workspaces/egress`, writes `/app/var/egress/plan.json`,
builds a local namespace lab (public, app, data, NAT, endpoint, and external
peers), sends TCP/UDP probes, and writes `/app/output/cutover-report.json`.
Reordering topology maps must not change routing semantics. Adding one AZ
must create only the corresponding per-AZ behavior.

## Report schema

`/app/output/cutover-report.json` fields:

- `status` — `READY` or `FAILED`
- `reason` — null on success, otherwise a short failure class
- `policy_errors` — list of plan policy violations
- `namespaces` — list of `{name, kind, az}` created for the lab
- `flows` — list of `{id, src, dst, protocol, path, translated_source, allowed}`
- `nat_decisions` — map of AZ key to `{health, new_flow_action}`
- `dns` — map of interface service short name to private answer host
- `gateway_bypass` — map of gateway service to boolean (true when path skips NAT)
- `data_isolated` — boolean
- `migration` — `{legacy_keys, destructive_actions}`
- `report_digest` — sha256 over the stable semantic subset

`/app/var/egress/plan.json` is the regenerated `terraform show -json` plan.
