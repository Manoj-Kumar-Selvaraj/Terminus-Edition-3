# terraform-aws-zonal-egress-drain-cutover

Edition 3 migration of the private-egress cutover theme into a zonal NAT
drain rehearsal. Graded on Terraform plan semantics plus simulated
namespace traffic paths — not a static resource checklist.

## Novelty

Distinct from claims-edge HTTP routing, Windows→Linux wave handoff, and
EKS add-on trust rollouts. This task is about same-AZ egress, data-tier
isolation, gateway vs interface endpoint paths, and drain-safe NAT
behavior under legacy state continuity.

## Verification

Separate verifier re-plans the submitted module with hidden topologies,
legacy state, and NAT failure schedules, then runs the trusted egress lab.
Oracle reward 1 / NOP reward 0 required.
