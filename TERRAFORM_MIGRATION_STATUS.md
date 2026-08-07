# Terraform Edition 2 → 3 Migration Status

Started: 2026-08-06. Edition-2 is **read-only** (no edits/restores). Authority: `TERMINUS_3_AI_INSTRUCTIONS.md` + Cursor Edition-3 rules + `terraform-edition-2-to-3.mdc`.

## Source inventory (rechecked 2026-08-06)

| # | Source | WT files | HEAD files | Destination | State |
|---|--------|----------|------------|-------------|-------|
| 1 | `terraform-aws-cloudfront-waf-origin-lockdown` | 45 | 0 (untracked) | `terraform-aws-claims-edge-exception-cutover` | **complete** |
| 2 | `terraform-aws-ec2-windows-linux-cutover-plan` | 4 | 21 | `terraform-aws-windows-linux-wave-transition` | **complete** |
| 3 | `terraform-aws-eks-addons-irsa-upgrade-recovery` | 3 | 20 | `terraform-aws-eks-addon-trust-rollout` | **complete** |
| 4 | `terraform-aws-eks-jenkins-controller-fleet-recovery` | 1 | 45 | `terraform-aws-jenkins-controller-cell-upgrade` | **complete** |
| 5 | `terraform-aws-lambda-jenkins-pipeline-cutover-recovery` | 0 | 65 | `terraform-aws-lambda-settlement-dual-run-cutover` | **complete** |
| 6 | `terraform-aws-private-egress-cutover-plan-recovery` | 1 | 33 | `terraform-aws-zonal-egress-drain-cutover` | **complete** |
| 7 | `terraform-aws-private-egress-cutover-security` | 2 | 0 | `terraform-aws-private-service-access-boundary` | **blocked** (HEAD empty; WT only unsafe stub) |
| 8 | `terraform-aws-vpc-endpoint-routing-recovery` | 0 | 50 | `terraform-aws-split-horizon-endpoint-migration` | **complete** |
| 9 | `terraform-aws-vpc-module-egress-recovery` | 0 | 58 | `terraform-aws-vpc-reconciliation-controller` | **complete** |
| 10 | `terraform-azure-vnet-private-endpoint-cutover-recovery` | 0 | 66 | `terraform-azure-spoke-private-endpoint-transition` | **complete** |
| 11 | `terraform-state-lock-contention` | 0 | 38 | `terraform-http-backend-concurrency-incident` | **complete** |
| 12 | `terraform-aws-ec2-module-rollout-recovery` | 0 | 56 | `terraform-aws-ec2-fenced-fleet-rollout` | **complete** |

Existing E3 novelty baselines: `terraform-live-edge-canary-cutover`, `terraform-aws-eks-weekend-fleet-cutover-plan`.

## Per-task log

### 1. terraform-aws-claims-edge-exception-cutover
- Source: WT complete (untracked E2 construction); E2 left untouched
- Novelty: live HTTP path/cache/signed/OAC lab — not canary/DNS
- Checks: Harbor oracle **1.0** (10 pytest); NOP **0.0**; `/app/var/edge` parent created in agent image
- Calib: pending

### 2. terraform-aws-windows-linux-wave-transition
- Source inspected via `git show HEAD:...` (WT partial/deleted); E2 left untouched
- Novelty: dependency-wave rehearsal with exclusive disk mounts / writer handoff — not HTTP edge or EKS weekend fleet
- Checks: Harbor oracle **1.0**; NOP **0.0**
- Calib: pending

### 3. terraform-aws-eks-addon-trust-rollout
- Source via `git show HEAD:...`; E2 untouched
- Novelty: in-place addon/IRSA upgrade under drain/interruption — not fresh weekend fleet
- Checks: Harbor oracle **1.0**; NOP **0.0**
- Calib: pending

### 4. terraform-aws-jenkins-controller-cell-upgrade
- Source via `git show HEAD:...` (WT nearly empty); E2 untouched
- Novelty: three-cell Jenkins isolation / fleet registry / restart+rollback lab — not EKS addon trust
- Checks: Harbor oracle **1.0**; NOP **0.0** (via [Build Jenkins cell upgrade](36b1b2a1-6e85-43b9-8129-3e9f8742a7f3))
- Calib: pending

### 5. terraform-aws-lambda-settlement-dual-run-cutover
- Source via `git show HEAD:...` (WT deleted); E2 untouched
- Novelty: dual-run settlement Go controller + sealed ledger/notify/DLQ runtime — not edge/wave/addon labs
- Checks: Harbor oracle **1.0**; NOP **0.0** (via [Build lambda dual-run cutover](e7d56b9c-471b-45ea-b617-2b91ed9c326d))
- Calib: pending

### 6. terraform-aws-zonal-egress-drain-cutover
- Source via `git show HEAD:...` (WT deleted); E2 untouched
- Novelty: namespace NAT-drain / gateway / PrivateLink traffic lab — not static plan checklist
- Checks: Harbor oracle **1.0**; NOP **0.0** (via [Build zonal egress drain cutover](1a515d75-94a7-4b0a-99b3-a26689db57b2))
- Calib: pending

### 7. terraform-aws-private-service-access-boundary
- **Blocked**: HEAD has 0 files; WT has only unsafe starter module remnant. Insufficient source for fair reconstruction without inventing the domain from the name alone. Migration design exists in rule, but no-restore rule + empty HEAD = blocker until user restores source or authorizes design-only construction from the rule text.

### 8. terraform-aws-split-horizon-endpoint-migration
- Source via `git show HEAD:...` (WT deleted); E2 untouched
- Novelty: endpoint kind + split-horizon DNS + state identity / consumer root — not zonal NAT drain or VPC reconciler
- Checks: Harbor oracle **1.0**; NOP **0.0** (via [Build split-horizon endpoint migration](2f959244-13d3-4aff-a361-23cd883b5318))
- Calib: pending

### 9. terraform-aws-vpc-reconciliation-controller
- Source via `git show HEAD:...` (WT deleted); E2 untouched
- Novelty: Go reconciler + black-box control-plane + SQLite/WAL — not zonal NAT drain or split-horizon DNS
- Checks: Harbor oracle **1.0**; NOP **0.0** (via [Build VPC reconciliation controller](66e8c347-3eba-4d14-aa54-0664f9a0ea8c))
- Calib: pending

### 10. terraform-azure-spoke-private-endpoint-transition
- Source via `git show HEAD:...` (WT empty); E2 untouched
- Novelty: Azure spoke PE / UDR / NSG / private DNS lab with mock azurerm — not AWS VPC family
- Checks: Harbor oracle **1.0**; NOP **0.0** (via [Build Azure spoke PE transition](f39df480-ff5f-4348-b4e2-a1cb465c405e))
- Calib: pending

### 11. terraform-http-backend-concurrency-incident
- Source via `git show HEAD:...` (WT deleted); E2 untouched
- Novelty: real HTTP backend + SQLite locks/lineage with concurrent TF CLI — not a state-file simulator
- Checks: Harbor oracle **1.0**; NOP **0.0** (via [Build HTTP backend concurrency](443ed0e9-4b6c-41a9-acf6-b38f3dfa2acb))
- Calib: pending

### 12. terraform-aws-ec2-fenced-fleet-rollout
- Source via `git show HEAD:...` (WT deleted); E2 untouched
- Novelty: fenced Go rollout controller + verifier-owned EC2 control plane — not Windows wave or plan-only module recovery
- Checks: Harbor oracle **1.0**; NOP **0.0** (via [Build fenced EC2 fleet rollout](58ac1a43-b2ab-4edf-ab79-4c310e42a2c0))
- Calib: pending

## Final compact report (2026-08-06)

### Completed destinations (11)
| # | Destination | Oracle | NOP |
|---|-------------|--------|-----|
| 1 | `terraform-aws-claims-edge-exception-cutover` | 1.0 | 0.0 |
| 2 | `terraform-aws-windows-linux-wave-transition` | 1.0 | 0.0 |
| 3 | `terraform-aws-eks-addon-trust-rollout` | 1.0 | 0.0 |
| 4 | `terraform-aws-jenkins-controller-cell-upgrade` | 1.0 | 0.0 |
| 5 | `terraform-aws-lambda-settlement-dual-run-cutover` | 1.0 | 0.0 |
| 6 | `terraform-aws-zonal-egress-drain-cutover` | 1.0 | 0.0 |
| 8 | `terraform-aws-split-horizon-endpoint-migration` | 1.0 | 0.0 |
| 9 | `terraform-aws-vpc-reconciliation-controller` | 1.0 | 0.0 |
| 10 | `terraform-azure-spoke-private-endpoint-transition` | 1.0 | 0.0 |
| 11 | `terraform-http-backend-concurrency-incident` | 1.0 | 0.0 |
| 12 | `terraform-aws-ec2-fenced-fleet-rollout` | 1.0 | 0.0 |

### Blocked (1)
| # | Destination | Reason |
|---|-------------|--------|
| 7 | `terraform-aws-private-service-access-boundary` | HEAD empty (0 files); WT only unsafe stub; no-restore rule prevents reconstruction |

### Checks run (each completed task)
- Harbor `terminus3.ps1 oracle` → reward 1.0
- Harbor `terminus3.ps1 nop` → reward 0.0
- Task-local pytest suites inside verifier image
- Model difficulty calibration (GPT×5 + Opus×5): **pending** for all destinations

### Files created/changed
- New under `Terminus-Edition-3/` for each destination above (instruction, task.toml, README, environment/, solution/, tests/)
- `Terminus-Edition-3/TERRAFORM_MIGRATION_STATUS.md` (this file)

### Terminus-Edition-2
**Not modified** by this migration. Sources inspected via working tree and/or `git show HEAD:` only; no restore/checkout of deleted E2 paths.
