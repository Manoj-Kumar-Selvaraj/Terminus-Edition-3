# terraform-aws-split-horizon-endpoint-migration

Edition 3 conversion of the VPC endpoint routing theme. The scored center is
endpoint kind, split-horizon DNS views, and non-destructive state identity —
not zonal NAT drain (`terraform-aws-zonal-egress-drain-cutover`) or VPC
reconciliation controllers (`terraform-aws-vpc-reconciliation-controller`).

## Why it is hard

Gateway vs interface placement, private-zone ownership, security-group scope,
downstream output contracts, and `moved` identity all interact. A plan that
looks complete but leaks private answers into the public view, attaches a
gateway endpoint to a public route table, or replaces stable resources fails
the lab and migration checks.

## Verification

Separate verifier replans the submitted module (including hidden catalog and
ordering variants), plans the consumer root, plans against a legacy state
fixture, runs the DNS/reachability lab, and grades `/app/output/migration-evidence.json`.

## Base image

Canonical Python 3.13 slim bookworm (digest-pinned). Terraform, the AWS
provider mirror, and dnsmasq are baked at build time for offline planning and
local split-horizon queries.
