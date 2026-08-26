"""Parameter group management, inheritance resolution, reset, and comparison engine."""
from typing import Any, Dict, List, Optional, Tuple
from rds.parameter_catalog import ParameterCatalog
from rds.parameter_group import ParameterGroupManager
from rds.errors import ParameterGroupError


class ParameterGroupOrchestrator:
    """Orchestrates DBParameterGroup lifecycle, inheritance trees, and comparison."""

    def __init__(self, catalog: ParameterCatalog = None):
        self.catalog = catalog or ParameterCatalog()

    def create_parameter_group(
        self,
        group_name: str,
        family: str = "postgres16",
        description: str = "",
        initial_overrides: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a new DBParameterGroup with inherited family defaults and custom overrides."""
        overrides = initial_overrides or {}

        validation_errors = []
        for param_name, param_val in overrides.items():
            valid, err = self.catalog.validate_parameter_value(param_name, str(param_val))
            if not valid:
                validation_errors.append(err)

        if validation_errors:
            raise ParameterGroupError(f"Parameter group validation failed: {'; '.join(validation_errors)}")

        merged_params = ParameterGroupManager.merge_parameter_overrides(family, overrides)

        return {
            "parameter_group_name": group_name,
            "family": family,
            "description": description,
            "parameters": merged_params,
            "custom_overrides": overrides,
        }

    def copy_parameter_group(
        self,
        source_group: Dict[str, Any],
        target_group_name: str,
        target_description: str = ""
    ) -> Dict[str, Any]:
        """Copy an existing DBParameterGroup to a new group name."""
        return {
            "parameter_group_name": target_group_name,
            "family": source_group.get("family", "postgres16"),
            "description": target_description or f"Copy of {source_group.get('parameter_group_name')}",
            "parameters": dict(source_group.get("parameters", {})),
            "custom_overrides": dict(source_group.get("custom_overrides", {})),
        }

    def modify_parameter_group(
        self,
        group: Dict[str, Any],
        modifications: Dict[str, str]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Modify parameters in parameter group and classify into immediate dynamic vs pending static."""
        family = group.get("family", "postgres16")
        current_params = group.get("parameters", {})

        validation_errors = []
        for param_name, param_val in modifications.items():
            valid, err = self.catalog.validate_parameter_value(param_name, str(param_val))
            if not valid:
                validation_errors.append(err)

        if validation_errors:
            raise ParameterGroupError(f"Modify parameter group failed: {'; '.join(validation_errors)}")

        updated_params, pending_static = ParameterGroupManager.classify_and_apply_parameters(
            family, current_params, modifications
        )

        custom_overrides = dict(group.get("custom_overrides", {}))
        custom_overrides.update(modifications)

        # Keep pending static values available for reboot apply without mutating runtime map.
        pending_values = {name: modifications[name] for name in pending_static if name in modifications}

        updated_group = {
            "parameter_group_name": group["parameter_group_name"],
            "family": family,
            "description": group.get("description", ""),
            "parameters": updated_params,
            "custom_overrides": custom_overrides,
            "pending_static_values": pending_values,
        }

        return updated_group, pending_static

    def reset_parameter_group(
        self,
        group: Dict[str, Any],
        reset_all: bool = True,
        reset_parameters: Optional[List[str]] = None,
        attached_instances: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Reset parameter group to inherited family defaults and mark instances pending-reboot."""
        family = group.get("family", "postgres16")
        defaults = ParameterGroupManager.get_family_defaults(family)

        if reset_all:
            reset_group = {
                "parameter_group_name": group["parameter_group_name"],
                "family": family,
                "description": group.get("description", ""),
                "parameters": defaults,
                "custom_overrides": {},
            }
        else:
            custom_overrides = dict(group.get("custom_overrides", {}))
            current_params = dict(group.get("parameters", {}))

            if reset_parameters:
                for param in reset_parameters:
                    if param in custom_overrides:
                        del custom_overrides[param]
                    if param in defaults:
                        current_params[param] = defaults[param]

            reset_group = {
                "parameter_group_name": group["parameter_group_name"],
                "family": family,
                "description": group.get("description", ""),
                "parameters": current_params,
                "custom_overrides": custom_overrides,
            }

        instances = attached_instances or []
        marked = ParameterGroupManager.mark_instances_pending_reboot_after_reset(
            instances, group["parameter_group_name"]
        )
        return reset_group, marked

    def compare_parameter_groups(
        self,
        source_group: Dict[str, Any],
        target_group: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare parameter differences between two parameter groups."""
        src_params = source_group.get("parameters", {})
        tgt_params = target_group.get("parameters", {})

        diff = {}
        all_keys = set(src_params.keys()) | set(tgt_params.keys())

        for k in all_keys:
            v1 = src_params.get(k)
            v2 = tgt_params.get(k)
            if v1 != v2:
                diff[k] = {"source_value": v1, "target_value": v2}

        return {
            "source": source_group.get("parameter_group_name"),
            "target": target_group.get("parameter_group_name"),
            "different_parameters_count": len(diff),
            "differences": diff,
        }
