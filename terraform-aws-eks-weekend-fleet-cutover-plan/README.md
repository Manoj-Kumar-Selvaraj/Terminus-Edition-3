# terraform-aws-eks-weekend-fleet-cutover-plan

Human notes only. Agents never see this file.

## What the task is

Platform wants a review-board Terraform plan for the weekend fleet EKS control
plane — private cluster, two node pools (core on-demand + weekend spot), IRSA,
add-ons, Helm (including a Trivy node DaemonSet), Artifactory credential helper,
CPU alarms, Friday/Monday park schedules, and a placeholder ALB ingress.

The agent builds `environment/terraform/modules/eks_weekend_fleet` from scratch.
Root module, inventory, vendored charts and the two docs are frozen. The module
folder ships only `variables.tf` / `versions.tf` and stub outputs, so NOP cannot
accidentally look complete. Providers and charts are mirrored; the workspace is
`network_mode = "no-network"`.

Goals sit in `instruction.md`. Binding shapes, naming and permission envelopes
sit in `environment/terraform/docs/requirements.md` and
`security-review-notes.md`. Sizes, versions and flags come from
`weekend-fleet.auto.tfvars.json`.

## Why it bites

Most of the work is cross-resource agreement, not “create an eks_cluster”:

- No `data` / `import` / remote state. ARNs are composed from `account_id` and
  the naming table.
- The same IRSA ARN has to show up on the IAM role, any add-on that names that
  identity, and the Helm role-arn annotation. Trivy has an empty `irsa_role` and
  must not get an annotation.
- Trivy must be a Node-mode DaemonSet that can schedule on every worker
  (`Exists` toleration, no `nodeSelector`).
- Cutover payloads must only mention `weekend_parked` groups. Pulling the core
  pool into Friday scale-down is a quiet fail.
- After rendering the plan, `/app/environment/scripts/simulate-eks-weekend-cutover`
  steps Friday park → Monday restore on a synthetic fleet and writes
  `/app/output/eks_weekend_cutover_timeline.json`. A plan that merely “has two
  schedules” still fails if the timeline invariants break.
- Artifactory credentials are secretKeyRefs only — literals fail both the plan
  scan and a source scan of the module `.tf` files.
- `/app/output/eks_weekend_fleet_plan.json` has to be real `terraform show
  -json`, not a hand-written document.

## Difficulty

Advanced. From-scratch module against a dense contract, offline providers, and
several places where a plausible-looking plan still fails review.

## Base images / network

Agent: digest-pinned `python:3.13-slim-bookworm` plus a checksum-pinned
Terraform binary. Verifier: separate Python image with the pytest suite baked
in. No network at runtime — mirrors cover providers and charts.

## Verification

Separate verifier mounts the rendered plan JSON and the shipped module source.
Tests use a sealed copy of the inventory fixture and assert plan-time known
values plus cross-links (IRSA ↔ add-on ↔ Helm ↔ schedules ↔ outputs), not just
“resource exists”.

## Oracle

`solution/solve.sh` wipes the module `*.tf` files, copies the reference tree
from `solution/terraform/modules/eks_weekend_fleet`, runs
`/app/environment/scripts/render-eks-weekend-plan`, then
`/app/environment/scripts/simulate-eks-weekend-cutover`, and sanity-checks that
the plan is complete and the timeline reports `ok`. NOP leaves the empty shell
and scores 0.
