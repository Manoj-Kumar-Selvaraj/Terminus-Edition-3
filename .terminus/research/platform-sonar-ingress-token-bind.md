# Scenario research — platform-sonar-ingress-token-bind

Source repo: https://github.com/Manoj-Kumar-Selvaraj/Platoform-Deployment-template (HEAD 49158e1)
Profile: `large_system_strict` / infrastructure
Taxonomy: Software / Systems

## STATUS: CANDIDATES_READY

### Candidate A — Post-deploy Sonar token bind + shared ALB group (RECOMMENDED)

- PERSONA: platform engineer on the internal MVP (Jenkins + SonarQube + Artifactory behind one internet-facing ALB group).
- NORMAL_WORKFLOW: first `terraform apply` brings Jenkins/Sonar up with an empty analysis token; operator mints a Sonar global analysis token; second apply interpolates it into JCasC; `scripts/validate.sh` checks hostnames and `/api/system/status`.
- OBSERVED_INCIDENT: second apply “succeeded”; Jenkins `/login` is up; `withSonarQubeEnv` 401s; `sonar.platform.test` flaps on `platform-ingress`.
- DURABLE_STATE: Jenkins EFS home (uid 1000 AP), Sonar analysis journal (~12k scans), RDS identity ternary, ExternalDNS zone+TXT owner, SSM command log.
- REASONING_CHAIN: secret key / JCasC id / Helm mount / `serverUrl` (ingress, not JDBC) / shared group healthcheck / ExternalDNS sync owner / JDBC `address` vs `endpoint:5432` / SSM-only runner.
- PARTIAL_FIX_TRAPS: split the ALB group per host; point Jenkins at the RDS hostname; open SSH on the runner; disable ExternalDNS sync; bump `numExecutors` so scans run on the controller.
- SCALE_FIT: live local control plane + 30–50 TF/K8s resources + 20–30 manifestations. Not a business ledger; seed is CI scan history.
- REFERENCES: repo `kubernetes.tf` two-phase token bind; `docs/runbooks/domain-and-ingress.md`; `scripts/validate.sh`; JCasC `$${sonarqube-token}` interpolation.
- DUPLICATE_RISK: must not become jenkins-controller-cell-upgrade (3 cells), eks-addon-trust-rollout (IRSA/PDB), split-horizon VPC endpoints, live-edge canary weights, or ansible-ci-control-plane (Go CI). Must not use `/app/bin/X` + `plan.json` + READY digest.

### Candidate B — EFS dual-tenant Jenkins vs Artifactory

Same FS, Jenkins AP `/jenkins-home` uid 1000 vs Artifactory RWX 50Gi. Weaker alone; keep as a coupled invariant inside A.

### Candidate C — DR JDBC retarget

`enable_dr_restore` flips Sonar JDBC to a restored hostname while ingress `sonar.${domain}` and the token bind stay. Strong as a hidden variation of A, not a separate task.

### Candidate D — SSM-only Ansible dispatch

No SSH; empty inventory; `ANSIBLE_RUNNER_ID`. Too close to ansible-ci-control-plane as a standalone incident; couple into A as a safety axis.

### Candidate E — ExternalDNS sync-steal when adding artifactory.

Public TXT registry vs split-horizon private views. Couple into A.

## RECOMMENDATION

Candidate A. Public interface is reload + live probes (Jenkins creds, Sonar validate, host-header HTTP, zone+TXT, JDBC identity, EFS uid, SSM log) — not a READY digest.

## WHY_THIS_ONE

It is the repo’s actual post-deploy handshake and it couples secrets, ingress, DNS ownership, persistence, JDBC, and SSM. Existing Edition 3 Terraform tasks do not model that bind.

## Data-volume note

Primary business records are Sonar analysis journal rows (12k, varied projects/statuses/scanners/days). A 10k payment-style ledger would be fake for this control plane.
