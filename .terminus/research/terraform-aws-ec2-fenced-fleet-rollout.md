# WORK_PACKAGE_RESEARCH — terraform-aws-ec2-fenced-fleet-rollout

STATUS: RESEARCH_READY
CREATION_PROFILE: large_system_strict

## Chosen work package

Incident-driven **completion of a fenced payments EC2 fleet release plane**: repair the Go rollout controller and the Terraform EC2 module so a pilot-then-wave apply commits through a verifier-owned control plane, with interacting provenance, placement, capacity, volume, import, drift, fencing, and journal invariants.

Persona: payments SRE finishing a torn rolling refresh, not a greenfield ASG author.

## Candidates considered

1. Fenced EC2 fleet rollout (chosen) — Go controller + real Terraform + live CP inventory.
2. AMI catalog governance only — too small; no rollout state machine.
3. Terraform-only ASG module without controller — fails the conversion design (control plane truth).
4. Generic ASG refresh wrapper — reskin of EKS/Jenkins fleet tasks.

## Novelty vs Edition 3 peers

Not a reskin of:

- `stackyard-terraform-control-plane` — TFC-class run/lock UI.
- `terraform-aws-windows-linux-wave-transition` — guest disk/DNS rehearsal, not ASG fencing.
- `terraform-aws-eks-weekend-fleet-cutover-plan` — EKS node groups/Helm, plan-only.
- `terraform-live-edge-canary-cutover` — edge WAF/DNS canary.
- `terraform-aws-jenkins-controller-cell-upgrade` — Jenkins cells.

This product is slot-stable EC2 identity + owner-fenced pilot/wave + slot-owned EBS generations + imported moved addresses + report-only drift against a hashed control-plane binary.

## Scale fit

Natural packages: identity, IPAM/placement, network, IAM, volumes, rollout FSM, fence, drift, import, journal, CP client, Terraform module, operator. IPAM catalog supplies 12k varied org subnets. F2P diversity comes from those coupled surfaces, not fixture renames.

## Rejected padding

No decorative AWS resources to hit 30–50. No 10k fake ASG instances.
