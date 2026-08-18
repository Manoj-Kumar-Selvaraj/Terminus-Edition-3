# ansibleops managed resources

`ansibleops` is a Go Terraform provider for managing local Linux operating-system objects while using Ansible as the mutation backend. The provider runs from `/app/provider`, exposes the ten resource types documented in `/app/provider/docs/provider-contract.md`, and relies on Terraform Core as the only durable Terraform state authority.

## Operating model

Terraform owns desired state, dependency ordering and persisted resource state. Provider Create, Update and Delete operations translate managed-resource intent into bounded Ansible mutations. Read and refresh use native Linux observation so planning can detect external filesystem, content, account, group, symlink and crontab changes without replaying configuration management.

Resource identity is tied to each documented external object key rather than mutable settings. In-place changes therefore preserve identity, while mutation failures must leave the last successfully applied Terraform state available for retry. Delete operations are scoped to the object owned by the resource, including sibling-safe line/block/cron removal, symlink-target preservation and the documented user-home policy.

## Runtime layout

The provider source, configuration and operator documentation are under `/app/provider`:

- `cmd/terraform-provider-ansibleops/` contains the provider process entrypoint.
- `internal/provider/` owns registration, configuration and runtime preflight.
- `internal/resources/` implements the ten Terraform managed resources.
- `internal/ansible/` and `internal/runner/` own task generation and Ansible process execution.
- `internal/observe/` provides native Linux observation used by refresh.
- `internal/lifecycle/` contains shared identity, normalization and change helpers.
- `config/inventory.ini` is the local managed inventory used by the task environment.
- `docs/provider-contract.md`, `docs/resource-reference.md` and `docs/lifecycle.md` are the authoritative solver-visible technical contracts.

## Reliability and safety boundaries

Ansible process execution must preserve literal arguments, propagate non-zero exits and cancellation/timeout failures, and clean generated playbooks on every terminal path. Equivalent modes, unordered values, account observations and cron defaults must normalize consistently so repeated apply/plan/refresh cycles converge without unnecessary mutation.

The supported scope is a deterministic local Linux target. Remote fleet orchestration, dynamic inventory, Ansible Vault/Galaxy workflows, Windows targets, arbitrary playbook resources and provider-owned Terraform state storage are outside this package's contract.
