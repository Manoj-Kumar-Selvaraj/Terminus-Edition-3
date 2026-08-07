# terraform-aws-vpc-reconciliation-controller

Edition 3 conversion of the VPC module egress recovery theme into a
controller-driven reconciliation incident. Observed cloud state lives behind
a black-box HTTP control-plane; durable progress is SQLite/WAL. Graded on
live control-plane mutations, journal fencing, Terraform plan semantics, and
the reconciliation report — not on HCL labels or static recovered JSON.

## Novelty

Distinct from zonal egress drain (packet paths / NAT drain staging) and
split-horizon endpoint migration (DNS views / endpoint kinds). This task is
about fenced multi-stage reconciliation against a mutable control-plane with
import moves, audit drift, and restart safety.

## Why it is hard

Route health, endpoint associations, CIDR identity, flow-log scope, and
resolver drift all interact. Fixing routes without imported app table IDs
breaks endpoints; committing before CIDR validation leaves partial state;
resume without owner/digest/token fencing duplicates effects.

## Verification

Separate verifier starts a trusted control-plane with hidden seed variants,
rebuilds the submitted controller, re-plans Terraform, and checks fail-closed
errors, lost-response resume, idempotent digests, and plan/control-plane
agreement. Oracle reward 1 / NOP reward 0 required.

## Base image

Canonical Python 3.13 slim Bookworm final runtime with a digest-pinned Go
1.24 toolchain copied from the canonical golang builder stage, plus baked
Terraform 1.9.8 and an offline AWS provider filesystem mirror.
