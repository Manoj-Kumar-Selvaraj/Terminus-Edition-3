# Fenced EC2 fleet rollout contract

Offline release controller for a private payments fleet. Terraform expresses desired launch template, ASG, security, IAM, and slot-owned volumes. The Go controller plans and applies a fenced pilot-then-wave rollout against a local EC2 control plane. Observed inventory on the control plane is authoritative.

## Configuration

Input schema `ec2-module-config.v2` is loaded from `/app/data/fleet_config.json` unless overridden. Required families: `release_artifact`, `ami_catalog`, `asg`, `placement`, `network`, `ebs_volumes`, and `rollout.owner_token`.

`release_artifact` is authoritative. Never select `ami_catalog.latest`. Manifest digest is lowercase SHA-256 of canonical JSON over keys `manifest_version`, `ami_id`, `ami_owner_account_id`, `architecture`, `commit_sha`, `build_id`, `user_data_sha256` (sorted keys, compact separators). `manifest_sha256` is not part of its own input.

## Launch template and identity

Launch-template AMI, architecture, user-data hash, and provenance come from the approved artifact. Provenance is exactly `{commit_sha, build_id, manifest_sha256}`. Version is a deterministic digest of immutable release identity, instance type, metadata options, and bootstrap hash. Reordering JSON keys must not change identities.

Require IMDSv2 (`http_tokens=required`, endpoint enabled, hop limit 1). Tags carry `Application`, `Environment`, `CommitSha`, `BuildId`, and `ReleaseManifestSha256`. Instance tags also include `Slot` as the decimal string of the zero-based integer slot.

## Placement and network

Only `tier: private_app` subnets in the configured account with unique IDs and AZs are eligible. Preserve existing slot placements under subnet reorder; balance new capacity across sorted AZs. No public IPs. Security-group ingress is ALB-only on `service_port`. Egress is HTTPS to sorted endpoint prefix lists plus UDP/TCP DNS to the resolver security group.

## Rollout

`operation_id` is deterministic for app, environment, prior/target manifests, and desired capacity. Strategy is `pilot-then-wave`. At most `asg.max_unavailable` instances may be unavailable. Pilot launches and becomes healthy before retirement. Waves of size `asg.wave_size` launch, health-check, then commit. Event names live in field `event`. Sequence: `pilot_launched`, `pilot_healthy`, `pilot_committed`, then wave trios, then `rollout_completed`. Failures emit `pilot_unhealthy` or `wave_unhealthy` then `previous_capacity_preserved` and roll back to the prior fleet.

`fault_point: after_pilot_commit_response_lost` commits the pilot, persists durable state/journal, sets `control_plane_response_lost`, and exits apply with status 3. Resume without the fault must not duplicate identities or events. A different `owner_token` fails with `stale rollout owner`. A target release change mid-operation fails with `target release changed`.

## Volumes

Each slot owns one volume per `logical_name`. Volume IDs derive from app/slot/name, not transient instance IDs. Encryption and account-scoped KMS are required; `delete_on_termination` is false. `attachment_generation` increments exactly once when the attached instance changes; `attachment_token` is the first 24 hex chars of SHA-256 over canonical `generation`, `instance_id`, and `volume_id`.

## Import, drift, journal

Legacy state recovers slot from `Slot` tags and preserves imported instance IDs when release and capacity are unchanged. Declare the documented `moved` blocks in `state_migrations.tf`. Manual drift in launch-template version, public IP, subnet, or security group is `report_only`. Truncate only an invalid final journal line; interior corruption fails with `invalid interior journal record`.

## Control plane and operator

The trusted control plane binary is `/opt/ec2-controlplane`. Controllers commit rendered inventory through it; local state alone is not proof. Operator entrypoint `/app/bin/fenced-fleet-rollout` regenerates `/app/var/fleet/plan.json`, applies through the control plane, and writes `/app/output/rollout-report.json` with fields `status`, `report_digest`, `state_digest`, `control_plane_state_digest`, `refresh_status`, `instance_count`, `volume_count`, `operation_id`, and release identity. Success requires `status: READY` and matching controller/control-plane digests. A second identical run must keep the same `report_digest`.

## IAM

Least-privilege statements (Effect Allow only): `SsmControlPlane`, `ReadReleaseArtifact`, `DecryptDataVolume`, `PublishPaymentsMetrics` with the actions, resources, and conditions documented in evidence and the recovery notes under `/app/docs`. Wildcard actions are forbidden.
