The Terraform control plane under `/app/stackyard` is supposed to let operators manage orgs, workspaces, variables, runs, and state locks from a browser and a JSON API, with SQLite underneath. Behavior is drifting off the shipped contract, so bring API and UI back in line without reshaping the public tree.

Treat `/app/stackyard/docs/control-plane-contract.md` as binding for routes, payloads, run lifecycle, locks, variables, terraform argv mapping, audit, and how the UI talks to the API. After Go changes, rebuild so `/app/stackyard/bin/stackyard` is the binary you start.

- Wire startup through the documented env vars (`STACKYARD_DB`, `STACKYARD_ADDR`, `STACKYARD_DATA`, `TERRAFORM_BIN`, `STACKYARD_TOKEN`, `STACKYARD_SYNC`) instead of hard-coding paths or ports.
- Apply `/app/stackyard/db/schema.sql` on boot, seed org `acme`, and serve the static UI from `/app/stackyard/ui` at `/`.
- Runs, locks, and workspace deletes have to follow the contract’s safety rules: one active run at a time, apply/destroy only under the right lock, unlock only by the holder, legal discard/cancel transitions, and no deleting a busy workspace.
- Sensitive variables stay redacted on read; terraform/env vars still reach the runner as `TF_VAR_*` or plain env; destroy maps to the documented terraform argv; run and lock transitions leave the required audit trail.
- Keep the UI forms on the same API fields the contract defines, and show API errors instead of failing quietly. Execute through `/app/stackyard/bin/terraform-shim` (or `TERRAFORM_BIN`). A fresh DB boot of the repaired binary should satisfy the contract for both API and UI flows.
