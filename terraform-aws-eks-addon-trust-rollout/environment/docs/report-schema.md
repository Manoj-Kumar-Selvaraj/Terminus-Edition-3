# Upgrade Report Schema Contract

`/app/output/upgrade-report.json` records the complete evaluation of the EKS upgrade rollout.

## Schema Fields

- `status`: `"READY"` or `"FAILED"`
- `reason`: Null on success; error class string on failure.
- `policy_errors`: List of plan or policy validation error messages.
- `upgrade_order`: List of add-on names in actual rollout order.
- `steps`: List of step objects `{ "addon", "from_version", "to_version", "ok" }`.
- `availability`: Map of core service names to boolean availability status.
- `pdb_respected`: Boolean indicating whether PodDisruptionBudgets were respected during drain.
- `drain_result`: Object `{ "node", "core_available", "evicted_count", "blocked_count" }`.
- `irsa_bindings`: Map of trust key to `{ "subject", "ok", "role_arn" }`.
- `cross_service_denied`: Boolean indicating whether cross-service trust isolation was verified.
- `regulated_placement`: Map of workload name to `{ "nodepool", "capacity_type", "ok" }`.
- `interruption`: Object `{ "handled", "regulated_still_on_demand" }`.
- `report_digest`: Canonical SHA-256 digest string computed over stable semantic report fields.
