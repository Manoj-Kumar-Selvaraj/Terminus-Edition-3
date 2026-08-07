# Spoke private-endpoint transition contract

The reusable module under `/app/terraform/modules/spoke` plans a payments spoke
VNet from `/app/data/topology.json`. Workload subnets with route tables enabled
send `0.0.0.0/0` to `firewall_private_ip` as `VirtualAppliance` with BGP route
propagation disabled. Platform subnets listed in `reserved_subnet_names` and the
`private_endpoint_subnet_key` stay outside that UDR set.

NSGs are created only where `nsg_enabled` is true. App-tier inbound allows TCP
from `application_gateway_subnet_cidr` on `app_ports`. Data-tier inbound allows
TCP from app subnet prefixes on 1433, 5432, and 6379. Every managed NSG denies
Internet-origin inbound traffic; broad Internet/`*`/`0.0.0.0/0` allows are
invalid. Private endpoints attach only to the private-endpoint subnet, with
network policies disabled there, a DNS zone group, and VNet links (registration
off) for the blob, queue, Key Vault, and PostgreSQL privatelink zones.

Diagnostics target the VNet and every managed NSG to
`log_analytics_workspace_id`. DDoS attachment follows `enable_ddos_protection`
against the supplied plan id — the module never creates the plan. A
`CanNotDelete` lock scopes the VNet. Governance tags in `/app/data/governance.json`
win over conflicting caller tags. Legacy singleton addresses listed there must
move into keyed resources so a plan against imported state does not replace
them. `allowed_admin_cidrs` rejects `0.0.0.0/0` and `::/0`.

`/app/bin/spoke-pe-transition` regenerates the plan, runs the local network/DNS
lab, and writes `/app/var/spoke/plan.json`, `/app/output/transition-report.json`,
and `/app/output/network-probes.json`. Report `status` is `READY` only when
routing, NSG decisions, and private DNS agree. Reordering topology maps must
not change semantics; a second identical run must keep the same `report_digest`.
