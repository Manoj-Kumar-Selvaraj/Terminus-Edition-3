# terraform-azure-spoke-private-endpoint-transition

Edition 3 migration of the Azure VNet private-endpoint cutover theme into
mock-provider Terraform plans plus a plan-driven network/DNS lab. Distinct from
AWS VPC/endpoint tasks: Azure UDRs, BGP propagation, NSG priorities, Private
DNS zone groups, DDoS attachment, management locks, and governance tag merge
are the interacting surface.

## Why it is hard

Egress, NSG decisions, endpoint placement, and private DNS must agree before a
private name is usable. Diagnostics, DDoS, locks, and tag governance interact
with the same topology. Hidden variants reorder maps, toggle DDoS, expand NSGs
or endpoints, and plan against legacy state.

## Verification

Separate verifier replans the submitted module with trusted and hidden
topologies, runs the lab, and checks migration safety. Oracle and NOP share the
same path.

## Base image

Canonical Python 3.13 slim bookworm (digest-pinned). Terraform is baked at
build time. A schema-compatible offline mock of `hashicorp/azurerm` 3.116.0 is
compiled into the filesystem provider mirror because live Azure credentials are
not available in the lab; agent and verifier use the same mirror.
