# Add-on trust rollout contract

The regulated payments EKS cluster already exists. Inventory under `/app/data`
describes the current snapshot, the target add-on compatibility matrix, IRSA
trust observations, required PodDisruptionBudgets, and regulated placement
policy. Evidence under `/app/evidence` records the failed weekend attempt.

Terraform under `/app/terraform` must plan the target add-on versions and
scoped IRSA roles for EBS CSI, AWS Load Balancer Controller, and Karpenter.
Each role trusts exactly one `system:serviceaccount:<namespace>:<name>`
subject from `/app/data/trust_observations.json`. Policies stay limited to
that controller's work — no node-admin, no wildcard Action/Resource, and no
shared trust across controllers. System node capacity keeps the
`CriticalAddonsOnly` taint from `/app/data/defaults.json`. Regulated
placement allows only on-demand capacity on the approved node pool. Resources
tagged `UpgradeProtected=true` represent existing cluster identity and must
not be deleted or replaced in the plan.

Kubernetes manifests under `/app/k8s` must supply the required PDBs, system
controller service accounts with matching role annotations, and regulated
workload placement rules. The public operator `/app/bin/addon-trust-rollout`
plans Terraform offline, applies those manifests into the local upgrade lab,
advances add-ons only after prerequisites are ready, drains a system node,
and injects an interruption. `/app/output/upgrade-report.json` is `READY`
only when availability, PDB respect, IRSA bindings, denied cross-service
access, and regulated placement all hold. Reordering inventory maps must not
change upgrade semantics.

## Report schema

`/app/output/upgrade-report.json` fields:

- `status` — `READY` or `FAILED`
- `reason` — null on success, otherwise a short failure class
- `policy_errors` — list of plan policy violations
- `upgrade_order` — ordered addon names actually advanced
- `steps` — list of `{addon, from_version, to_version, ok}`
- `availability` — map of core service name to boolean
- `pdb_respected` — boolean
- `drain_result` — `{node, core_available, evicted_count, blocked_count}`
- `irsa_bindings` — map of trust key to `{subject, ok}`
- `cross_service_denied` — boolean
- `regulated_placement` — map of workload to `{nodepool, capacity_type, ok}`
- `interruption` — `{handled, regulated_still_on_demand}`
- `report_digest` — sha256 over the stable semantic subset

`/app/var/upgrade/plan.json` is the regenerated `terraform show -json` plan.
