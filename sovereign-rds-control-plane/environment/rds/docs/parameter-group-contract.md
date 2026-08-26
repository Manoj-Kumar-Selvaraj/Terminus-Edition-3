# Parameter Group Classification & Application Contract

Database parameter groups define runtime configuration parameters for PostgreSQL instances.

## Classification Rules

1. **Apply Type**:
   - `dynamic`: Modifying dynamic parameters applies changes immediately to the running database process.
   - `static`: Modifying static parameters sets `pending_reboot_parameters = true` on the instance without mutating runtime settings.

2. **Parameter Inheritance**:
   - Instance parameters inherit family default settings (e.g. `postgres16`).
   - Overriding specific parameters merges custom key-values into the inherited family default map rather than replacing the parameter map.

3. **Reboot & Boot Validation**:
   - Calling `RebootDBInstance` reloads static parameters from the parameter group.
   - If all static parameters pass boot validation, `pending_reboot_parameters` is cleared (`false`).
   - Calling `ResetDBParameterGroup` marks attached instances with `parameter_group_status = pending-reboot` and `pending_reboot_parameters = true`.
