# terraform-ansible-managed-resources

This work package completes an inherited Go Terraform provider that manages local Linux filesystem, content, account and cron objects while using Ansible for mutations. The provider lives at `/app/provider`; Terraform Core remains the durable state authority and the supplied provider/resource/lifecycle documents define the public operating contract.

## Why the repair is non-trivial

The resources share lifecycle and execution layers, so a plausible local fix can still leave another resource family wrong. Identity has to remain stable while native refresh exposes drift, mutation failures must not advance Terraform state, and deletion has to respect ownership boundaries for shared files, crontabs, symlinks and user homes. Runner correctness also matters because Terraform cancellation, timeouts and literal path data cross the provider/Ansible process boundary.

## Reference repair

The reference implementation repairs the shared lifecycle model rather than special-casing verifier scenarios: identities derive from external object keys, native observers drive refresh, state publication follows successful mutation, delete failures remain retryable, equivalent values are normalized, and the Ansible runner owns process outcome and temporary-playbook cleanup.

## Verification design

The separate verifier rebuilds the submitted `/app/provider` tree and exercises it with Terraform CLI against real local Linux state. The current suite has 30 F2P and 4 P2P scenarios spanning provider/state preservation, drift, update recovery, scoped deletion, account/group state, cron normalization and runner failure handling. The classifications remain design-time expectations until the deterministic starter/NOP and reference-solution matrices are executed; this README does not claim those empirical gates have passed.
