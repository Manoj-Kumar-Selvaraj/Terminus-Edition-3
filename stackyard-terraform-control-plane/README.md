# stackyard-terraform-control-plane

Edition 3 task: repair an incomplete **Stackyard** control plane (Go + SQLite + static UI) so terraform-style workspace runs obey concurrency, lock fencing, secret redaction, env injection, lifecycle, and audit rules.

## Why it is hard

Defects are clustered across store policy, runner argv/env construction, audit persistence, and UI form wiring. Partial fixes often regress another invariant (for example allowing unlock-by-non-holder while tightening apply locks). Agents must infer behavior from `/app/stackyard/docs/control-plane-contract.md`, not from a bug list.

## Solution approach

Replace the broken policy/runner/audit/UI modules with implementations that match the contract, rebuild `bin/stackyard`, and verify with the terraform shim.

## Verification

Separate verifier image rebuilds the submitted tree, boots the server against a temp DB + terraform-shim, and runs behavioral pytest suites covering API negatives and UI/API smoke.
