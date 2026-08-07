# terraform-aws-eks-addon-trust-rollout

Edition 3 conversion of the EKS add-ons / IRSA upgrade theme into an
in-place add-on trust rollout lab. Graded on Terraform plan semantics plus
live lab consequences (upgrade order, PDBs, IRSA subjects, regulated
placement), not on HCL labels or hand-edited plan fixtures.

## Novelty

Distinct from `terraform-aws-eks-weekend-fleet-cutover-plan`, which plans a
fresh private weekend fleet. This task starts from an existing cluster
snapshot and grades an upgrade under drain and interruption.

## Why it is hard

Addon versions form a compatibility graph. IRSA trust, system-pool taints,
PDBs, and regulated Karpenter placement all have to agree during disruption.
Fixing one dimension without the others fails the lab.

## Verification

Separate verifier re-plans submitted modules with hidden inventory variants,
runs the trusted upgrade lab, and checks fail-closed / partial-progress /
idempotent digests. Oracle reward 1 / NOP reward 0 required.

## Base image

Canonical Python 3.13 slim Bookworm digest with baked Terraform 1.9.8 and
an offline AWS provider filesystem mirror.
