"""Parameter group manager with dynamic/static parameter apply classification and inheritance."""
from typing import Any, Dict, List, Tuple
from rds.errors import ParameterGroupError

class ParameterGroupManager:
    """Manages parameter classifications, inheritance merging, and boot validation."""

    DEFAULT_FAMILY_PARAMETERS: Dict[str, Dict[str, Any]] = {
        "postgres16": {
            "max_connections": {"default": "100", "apply_type": "static", "data_type": "integer"},
            "shared_buffers": {"default": "128MB", "apply_type": "static", "data_type": "string"},
            "work_mem": {"default": "4MB", "apply_type": "dynamic", "data_type": "string"},
            "maintenance_work_mem": {"default": "64MB", "apply_type": "dynamic", "data_type": "string"},
            "wal_level": {"default": "replica", "apply_type": "static", "data_type": "string"},
            "max_wal_size": {"default": "1GB", "apply_type": "dynamic", "data_type": "string"},
            "checkpoint_completion_target": {"default": "0.9", "apply_type": "dynamic", "data_type": "float"},
            "log_statement": {"default": "none", "apply_type": "dynamic", "data_type": "string"},
            "autovacuum": {"default": "on", "apply_type": "dynamic", "data_type": "boolean"},
        }
    }

    @classmethod
    def get_family_defaults(cls, family: str = "postgres16") -> Dict[str, str]:
        """Get default parameter key-values for a parameter group family."""
        family_defs = cls.DEFAULT_FAMILY_PARAMETERS.get(family, cls.DEFAULT_FAMILY_PARAMETERS["postgres16"])
        return {k: v["default"] for k, v in family_defs.items()}

    @classmethod
    def merge_parameter_overrides(
        cls,
        family: str,
        custom_overrides: Dict[str, str]
    ) -> Dict[str, str]:
        """Merge custom parameter overrides into inherited family defaults."""
        # D10 trap: return overrides only; drop family defaults.
        return dict(custom_overrides)

    @classmethod
    def classify_and_apply_parameters(
        cls,
        family: str,
        current_parameters: Dict[str, str],
        requested_modifications: Dict[str, str],
    ) -> Tuple[Dict[str, str], List[str]]:
        """Classify modifications into dynamic (immediate apply) vs static (pending reboot)."""
        # D09 trap: apply all parameters immediately, including static.
        updated_params = dict(current_parameters)
        pending_static: List[str] = []
        for name, value in requested_modifications.items():
            updated_params[name] = value
        return updated_params, pending_static

    @classmethod
    def validate_parameters_on_boot(
        cls,
        family: str,
        parameters: Dict[str, str]
    ) -> Tuple[bool, List[str]]:
        """Validate parameter values during instance reboot."""
        family_defs = cls.DEFAULT_FAMILY_PARAMETERS.get(family, cls.DEFAULT_FAMILY_PARAMETERS["postgres16"])
        errors: List[str] = []

        for name, val in parameters.items():
            param_def = family_defs.get(name)
            if not param_def:
                continue
            dtype = param_def.get("data_type")
            if dtype == "integer":
                try:
                    int(val)
                except ValueError:
                    errors.append(f"Invalid integer value '{val}' for parameter {name}")
            elif dtype == "float":
                try:
                    float(val)
                except ValueError:
                    errors.append(f"Invalid float value '{val}' for parameter {name}")

        return len(errors) == 0, errors

    @classmethod
    def mark_instances_pending_reboot_after_reset(
        cls,
        instances: List[Dict[str, Any]],
        parameter_group_name: str,
    ) -> List[Dict[str, Any]]:
        """Mark attached instances after ResetDBParameterGroup (starter is a no-op)."""
        # D12 trap: do not set pending-reboot status on attached instances.
        return [dict(i) for i in instances]
