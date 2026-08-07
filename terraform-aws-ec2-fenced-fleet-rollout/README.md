# terraform-aws-ec2-fenced-fleet-rollout

Frontier Edition 3 task: repair a Go fenced-fleet rollout controller and a real Terraform EC2 module so a pilot-then-wave release commits correctly through a verifier-owned EC2 control plane.

## Why it is hard

Multiple constraints interact: immutable release provenance, stable private slot placement, capacity-limited pilot/wave events, slot-owned encrypted volumes with generation-aware attachments, imported-state moves, report-only drift, owner fencing, and journal repair after a lost control-plane reply. Local JSON alone is not trusted — the control-plane inventory must match.

## Approach

Infer requirements from `/app/docs/fenced-fleet-contract.md` and the evidence under `/app/evidence`. Fix `/app/controller` and `/app/terraform`, then run `/app/bin/fenced-fleet-rollout`.

## Verification

The separate verifier replans submitted Terraform, rebuilds the submitted controller, drives hidden rollout/fault/inventory variants against its own control-plane binary, and checks report digests plus live inventory. Oracle must score 1; NOP must score 0.

## Base image

Final runtime uses the canonical Go Bookworm image so the agent can rebuild `fleetctl` from submitted controller sources. Terraform and the control-plane binary are baked at build time.
