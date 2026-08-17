# ansibleops provider contract

`ansibleops` is a Terraform provider for managing a bounded set of local Linux objects while using Ansible as the mutation backend. Terraform Core owns the physical Terraform state; the provider does not create or maintain a second durable state database.

## Runtime

The provider binary is `terraform-provider-ansibleops`. Terraform examples use source address `local/ansibleops`. The task container installs the provider in a filesystem mirror and configures Terraform to resolve that local provider without downloading it from a registry.

The supported target is the deterministic local Linux host represented by the supplied inventory. Provider configuration accepts an absolute inventory path, an `ansible-playbook` executable, a bounded execution timeout, and an absolute temporary-playbook directory. Generated playbooks are ephemeral runtime data.

## Ownership

One Terraform resource owns one external object key. Two resources must not manage the same path, user, group, or named cron entry. Terraform state contains resource configuration, stable provider identity, and observed/computed values; files, accounts, groups and crontab entries remain authoritative external state.

## Mutation and observation

Create, update and delete operations may invoke Ansible. Refresh/read operations are observation-only and inspect Linux state directly. A clean `terraform plan` or refresh must not execute Ansible.

Mutation commands are passed as process arguments, not shell command text. Non-zero process exits, timeouts and cancellation are failures. Temporary playbooks are removed after every terminal outcome. Provider diagnostics may report bounded execution failures, but command output is not persisted as resource state.

## State transitions

A successful create or update publishes state only after the requested external mutation completes. A failed update preserves the last successfully applied Terraform state. A destroy completes only after the owned object is absent or the provider has established that it was already absent.
