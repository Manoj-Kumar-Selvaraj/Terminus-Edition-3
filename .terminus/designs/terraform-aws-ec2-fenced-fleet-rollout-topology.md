# DEFECT_TOPOLOGY — terraform-aws-ec2-fenced-fleet-rollout

STATUS: TOPOLOGY_READY

Starter is a complete reachable system that takes the wrong branch at each coupled boundary. Partial fixes that correct only Terraform or only the Go facade still fail live CP matching.

## Root-cause clusters

- RC_IDENTITY — Release identity uses `ami_catalog.latest` and optional IMDS instead of the approved artifact digest.
- RC_VALIDATE — Manifest digest is not checked against canonical JSON; invalid catalogs still render.
- RC_PLACEMENT — Slots are reassigned from the current list order; IPAM tier/account eligibility is ignored.
- RC_NETWORK — Ingress is SSH/world; egress is unrestricted.
- RC_IAM — Single wildcard administrator statement.
- RC_VOLUME — Disks are unencrypted; attachment generation does not bump; token ignores canonical triple.
- RC_ROLLOUT — Pilot/wave events and rollback are skipped; lost-reply cursor is not persisted.
- RC_FENCE — Owner token and in-progress target-release changes are not enforced.
- RC_JOURNAL — Invalid lines are dropped regardless of position; tail is never marked truncated.
- RC_DRIFT — Manual public-IP/subnet/SG/LT drift schedules rolling replace.
- RC_IMPORT — Legacy Slot tags and moved addresses are ignored.
- RC_TFMODULE — Terraform module mirrors the identity/network/IAM/volume mistakes.

## Manifestations (24)

See `.terminus/designs/terraform-aws-ec2-fenced-fleet-rollout.json`.

## Partial-fix traps

- Pinning AMI in Terraform but leaving controller `ami-latest` still fails CP digest match.
- Closing the security group without least-privilege IAM still fails policy checks.
- Implementing waves without owner fencing still allows stale resume.
- Truncating every bad journal line hides interior corruption.
- Rewriting local JSON without committing through `/opt/ec2-controlplane` fails inventory match.

## Behavioral surfaces

- normal: first apply READY, provenance, encrypted slot volumes
- edge: odd capacity, extra AZ, reordered manifest keys, subnet reorder
- negative: invalid manifest, stale owner, target release changed, interior journal
- failure/recovery: fail_pilot, fail_wave, lost reply resume, torn tail
- cross-component: report-only drift vs replace; import moves + preserved instance IDs; CP digest vs local forge
