# SYSTEM_ARCHITECTURE — terraform-aws-ec2-fenced-fleet-rollout

STATUS: ARCHITECTURE_READY

Creation profile: `large_system_strict`
Implementation language: Go (solver-visible runtime) + Terraform HCL. Python is the operator/verifier driver.

This is the clean inherited system. No defects are injected here.

## COMPONENT_GRAPH

- `cmd/controlplane` — trusted EC2 inventory service; baked to `/opt/ec2-controlplane`
- `cmd/fleetctl` — plan/apply/validate CLI; rebuilds from submitted sources
- `controller` — facade (`ValidateConfig`, `Render`)
- `internal/types` — canonical JSON, hashing, value helpers
- `internal/ipam` — sqlite lookup of org subnets and AMI catalog
- `internal/validate` — config/schema/manifest/capacity/network/volume checks
- `internal/identity` — release provenance, launch-template version, IMDSv2
- `internal/placement` — private_app slot stickiness and AZ balance
- `internal/network` — ALB ingress, prefix-list HTTPS, resolver DNS
- `internal/iam` — four least-privilege statements
- `internal/volume` — slot-owned encrypted volumes, generation, attachment token
- `internal/rollout` — pilot-then-wave FSM, rollback, lost-reply cursor
- `internal/fence` — owner token and in-progress target-release guard
- `internal/drift` — report-only manual drift
- `internal/importdata` — Slot-tag recovery and documented moved addresses
- `internal/journal` — JSONL tail truncate vs interior fail-closed
- `internal/controlplane` — HTTP commit/inventory client
- `internal/render` — assemble inventory document and state_digest
- `terraform/modules/fleet` — LT, ASG, SG, IAM role/profile/policy, EBS, attachments, log group
- `bin/fenced-fleet-rollout` — plan Terraform, rebuild fleetctl, apply, write report

## ENTRYPOINTS

- `/app/bin/fenced-fleet-rollout`
- `/app/cmd/fleetctl` (`plan|apply|validate`)
- `/opt/ec2-controlplane` (`/healthz`, `/v1/inventory`, `/v1/commit`, `/v1/reset`)
- Config `/app/data/fleet_config.json`, IPAM `/app/data/ipam.sqlite`
- Contract `/app/docs/fenced-fleet-contract.md`

## STATE_MODEL

Authoritative observed inventory is the control-plane document after a successful commit. Local `/app/var/fleet/ec2_state.json` plus JSONL journal are durable operator state. Terraform expresses desired LT/ASG/SG/IAM/EBS; it does not replace CP truth. Volume IDs are slot-stable. Launch-template version is a digest of immutable release identity.

## SOLVER_VISIBLE_DOC_PLAN

- `docs/fenced-fleet-contract.md` — schemas, rollout events, IAM, journal, report
- `docs/iam-statements.md` — statement actions/resources/conditions
- `docs/ipam-catalog.md` — sqlite layout and eligibility
- evidence under `/app/evidence` including a lost-reply log

## PRODUCTION_CHARACTERISTICS

Differentiated Go packages, real Terraform plan, sqlite IPAM, JSONL journal with repair, HTTP control plane with owner fencing, restart/resume after lost reply, fail-closed validation.

## SCALE_FIT

12k IPAM subnets with account/AZ/tier variance. Controller packages are the production LOC, not seed SQL. Organic 25–30 F2P from provenance, placement, IAM/SG/EBS, FSM, fence, journal, drift, import, hidden capacity, anti-forge.

## RESOURCE_GRAPH

aws_launch_template, aws_autoscaling_group, aws_security_group, aws_iam_role, aws_iam_instance_profile, aws_iam_role_policy, aws_ebs_volume, aws_volume_attachment, aws_cloudwatch_log_group; CP state JSON; journal JSONL; plan.json; rollout-report.json.

## DATA_VOLUME_PLAN

`subnets` table: 12000 org IPAM rows. `images` catalog includes the approved AMI, latest alias, and holdout images. Fleet desired capacity remains small (config), which is realistic.

## UNRESOLVED_RISKS

- Terraform moved-block checks must use plan-against-legacy-state, not HCL greps.
- modernc.org/sqlite must be resolved at image build (`go mod tidy`).
- CRLF on Windows-authored scripts must be LF or the operator shebang fails.
