# Split-horizon endpoint migration contract

The reusable module under `/app/terraform/modules/network` owns the shared VPC,
public and private subnets, route tables, NAT default routes, gateway and
interface VPC endpoints, the endpoint security group, private hosted zones, and
the outputs the consumer workspace still reads. Inputs come from JSON under
`/app/data`. The staging workspace at `/app/terraform/workspaces/staging` wires
the module; `/app/terraform/workspaces/consumer` must plan against module
outputs without knowing module internals.

## Endpoint kinds

Gateway endpoints (`s3`, `dynamodb` in `/app/data/endpoints.json`) attach to
every private route table and must not attach to public route tables. NAT
default routes are not a substitute for gateway coverage.

Interface endpoints (`ssm`, `ssmmessages`, `ec2messages`) place only in private
subnets, enable private DNS, and share the endpoint security group. Public
subnets never host them.

## DNS views

Private hosted zones in `/app/data/dns_zones.json` associate only with the
owning VPC. Overlapping record names resolve from the private view to the
planned interface endpoint address for that zone's owner. The public view must
not inherit those private answers. SSM-family AWS names resolve privately only
when the matching interface endpoint has private DNS enabled and the querier is
in a private tier.

## Security

Ingress to the endpoint security group admits only sources listed in
`/app/data/allowed_sources.json` (security groups and private CIDRs). Open
world (`0.0.0.0/0`, `::/0`) is never acceptable for endpoint ingress.

## Outputs and identity

Publish legacy outputs `vpc_id`, `vpc_cidr_block`, `private_subnet_ids`,
`public_subnet_ids`, `private_route_table_ids`, `public_route_table_ids`,
`gateway_vpc_endpoint_ids`, `interface_vpc_endpoint_ids`,
`endpoint_security_group_id`, `endpoint_security_group_ids` together with
aggregates `network` and `endpoint_ids`. Values must be resource-backed.
List-indexed legacy addresses migrate to stable `for_each` keys through
`moved` blocks so planning against `/app/data/legacy_state.json` does not
replace unchanged VPC, subnet, route table, endpoint, or security group
identities.

## Operator command

`/app/bin/split-horizon-migrate` plans staging, plans the consumer, runs the
local split-horizon lab, and writes `/app/var/endpoint/plan.json` plus
`/app/output/migration-evidence.json`. Evidence fields: `status`,
`plan_digest`, `consumer_plan_digest`, `migration_safe`, `dns_probes`,
`reachability_probes`, `evidence_digest`. `status` is `READY` only when every
contracted probe passes and migration against legacy state is non-destructive
for preserved identities.
