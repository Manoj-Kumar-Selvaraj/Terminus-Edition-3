# Jenkins controller cell upgrade contract

The CI cluster already hosts three controller cells named in
`/app/data/fleet_registry.json`: `payments-controller`, `risk-controller`, and
`platform-controller`. Each cell owns its service account, home claim, routing
key, folder, and production jobs. The writable fleet registry and restrictions
under `/app/cells` must agree with that inventory. There is no proprietary
Operations Center resource — cell membership and job ownership come only from
the fleet registry.

Terraform under `/app/terraform` must plan:

- A dedicated controller node group sized for three cells, labeled for Jenkins
  controller work, tainted `dedicated=jenkins:NoSchedule`, and spread across the
  zones in `/app/data/node_topology.json`.
- One IRSA role per cell whose trust subject is exactly
  `system:serviceaccount:<namespace>:<service_account>` from the registry.
- One encrypted EFS access point (or equivalent exclusive home claim) per cell.
  Two cells must never share a claim path or filesystem identity.
- Cell plugin generation and disruption posture tagged so the lab can see
  `max_unavailable = 0` for controller pods during an AZ or upgrade fault.

Deploy config under `/app/cells` must pin plugins from the internal mirror with
the digests in `/app/data/plugin_catalog.json`, keep script console and
cross-cell job triggers off, and ship JCasC that disables signup. Only plugins
listed for a cell's target generation in `/app/data/compatibility_matrix.json`
may boot.

The public operator `/app/bin/cell-upgrade` plans Terraform offline, boots the
cells into `/app/var/cells`, submits registry jobs to their assigned cells,
restarts one controller, injects a failed upgrade on one cell while siblings
keep serving, rolls that cell back to the prior generation, and writes
`/app/output/cell-upgrade-report.json`. Status is `READY` only when isolation,
exclusive homes, preserved build watermarks, disruption respect, and successful
rollback all hold. Reordering registry maps must not change semantics.

## Report schema

`/app/output/cell-upgrade-report.json` fields:

- `status` — `READY` or `FAILED`
- `reason` — null on success, otherwise a short failure class
- `policy_errors` — list of plan or config policy violations
- `cells` — map of cell id to `{booted, plugin_generation, identity, home_claim, build_watermark, serving}`
- `job_runs` — list of `{job, cell, status, build_number}` for exercised jobs
- `isolation` — `{cross_cell_denied, dual_writer_blocked}`
- `restart` — `{cell, builds_preserved, watermark_after}`
- `upgrade_drill` — `{target_cell, failed, rolled_back, builds_preserved, sibling_cells_serving}`
- `disruption` — `{pdb_respected, other_cells_available}`
- `report_digest` — sha256 over the stable semantic subset

`/app/var/cells/plan.json` is the regenerated `terraform show -json` plan.
Runtime cell state lives under `/app/var/cells/<cell-id>/`.
