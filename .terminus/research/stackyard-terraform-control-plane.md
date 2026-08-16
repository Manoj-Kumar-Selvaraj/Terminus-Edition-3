# Research: stackyard-terraform-control-plane

## CREATION_RULE_CONTEXT
- CONTROL_PLANE_COMMIT: `1b42a75a40977919d567fc6d38b80cb58e17b2b7`
- RULE_SOURCES: `TERMINUS_3_AI_INSTRUCTIONS.md`, `CREATION_PIPELINE.md`, `PRODUCTION_AUTHENTICITY.md`, `INSTRUCTION_POLICY.md`
- CREATION_PROFILE: `large_system_strict`
- NETWORK/ENVIRONMENT: public; single-container agent image with Go toolchain + terraform shim; SQLite persistence
- KNOWN_POLICY_CONFLICTS: none

## Novelty
Existing Edition 3 terraform tasks author/fix HCL modules for AWS/Azure cutovers or HTTP backend concurrency. None ship a **Terraform Cloud replacement product** (UI + API + DB) that queues and executes terraform CLI operations.

Closest neighbors (distinct):
- `terraform-http-backend-concurrency-incident` — backend locking incident, not a TFC UI product
- `terraform-aws-*` / `terraform-live-edge-canary-cutover` — IaC module repair
- `platform-sonar-ingress-token-bind` — mentions TFC vars only as ops evidence

## Work package
Complete Stackyard, a self-hosted TFC-class control plane at `/app/stackyard`:
- UI for orgs, workspaces, variables, runs, locks, and command dispatch
- Go API orchestrating terraform CLI (`init|validate|fmt|plan|apply|destroy`)
- SQLite persistence for workspaces, vars, runs, locks, audit

Inherited starter is partially wired but incomplete across run fencing, locking, secret handling, variable injection, and lifecycle transitions. Agent must make the live system match `/app/stackyard/docs/control-plane-contract.md`.

## Domain fit
Software / Systems — control-plane concurrency, state locking, CLI orchestration, API/UI coupling.
