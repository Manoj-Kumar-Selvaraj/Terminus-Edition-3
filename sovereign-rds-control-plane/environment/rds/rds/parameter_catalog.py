"""Comprehensive PostgreSQL 16 parameter catalog definitions and validation rules."""
from typing import Any, Dict, List, Optional, Tuple

class ParameterCatalog:
    """PostgreSQL 16 parameter catalog rules and constraints."""

    POSTGRES_16_PARAMETERS: Dict[str, Dict[str, Any]] = {
        "max_connections": {
            "apply_type": "static",
            "data_type": "integer",
            "min_val": 10,
            "max_val": 8192,
            "default": "100",
            "description": "Sets the maximum number of concurrent database connections.",
        },
        "shared_buffers": {
            "apply_type": "static",
            "data_type": "string",
            "default": "128MB",
            "description": "Sets the amount of memory PostgreSQL uses for shared memory buffers.",
        },
        "work_mem": {
            "apply_type": "dynamic",
            "data_type": "string",
            "default": "4MB",
            "description": "Sets the maximum memory to be used by internal sort operations and hash tables.",
        },
        "maintenance_work_mem": {
            "apply_type": "dynamic",
            "data_type": "string",
            "default": "64MB",
            "description": "Sets the maximum memory to be used by maintenance operations.",
        },
        "wal_level": {
            "apply_type": "static",
            "data_type": "string",
            "allowed_values": ["minimal", "replica", "logical"],
            "default": "replica",
            "description": "Sets the level of information written to the WAL.",
        },
        "max_wal_size": {
            "apply_type": "dynamic",
            "data_type": "string",
            "default": "1GB",
            "description": "Sets the maximum size to let the WAL grow during automatic checkpoints.",
        },
        "checkpoint_completion_target": {
            "apply_type": "dynamic",
            "data_type": "float",
            "min_val": 0.0,
            "max_val": 1.0,
            "default": "0.9",
            "description": "Specifies the target duration for checkpoint completion.",
        },
        "log_statement": {
            "apply_type": "dynamic",
            "data_type": "string",
            "allowed_values": ["none", "ddl", "mod", "all"],
            "default": "none",
            "description": "Controls which SQL statements are logged.",
        },
        "autovacuum": {
            "apply_type": "dynamic",
            "data_type": "boolean",
            "allowed_values": ["on", "off"],
            "default": "on",
            "description": "Starts the autovacuum background worker process.",
        },
        "effective_cache_size": {
            "apply_type": "dynamic",
            "data_type": "string",
            "default": "4GB",
            "description": "Sets the planner's assumption about the effective size of the disk cache.",
        },
        "random_page_cost": {
            "apply_type": "dynamic",
            "data_type": "float",
            "min_val": 0.0,
            "max_val": 100.0,
            "default": "4.0",
            "description": "Sets the planner's estimate of the cost of a non-sequentially-fetched disk page.",
        },
        "seq_page_cost": {
            "apply_type": "dynamic",
            "data_type": "float",
            "min_val": 0.0,
            "max_val": 100.0,
            "default": "1.0",
            "description": "Sets the planner's estimate of the cost of a disk page fetch that is part of a series.",
        },
        "synchronous_commit": {
            "apply_type": "dynamic",
            "data_type": "string",
            "allowed_values": ["on", "off", "local", "remote_write", "remote_apply"],
            "default": "on",
            "description": "Sets the current transaction's level of synchronization for WAL commit.",
        },
        "archive_mode": {
            "apply_type": "static",
            "data_type": "string",
            "allowed_values": ["on", "off", "always"],
            "default": "on",
            "description": "Enables WAL archiving.",
        },
        "archive_command": {
            "apply_type": "dynamic",
            "data_type": "string",
            "default": "cp %p /app/rds/wal_archive/%f",
            "description": "Sets the shell command to execute to archive a completed WAL file segment.",
        },
        "checkpoint_timeout": {
            "apply_type": "dynamic",
            "data_type": "string",
            "default": "5min",
            "description": "Sets the maximum time between automatic WAL checkpoints.",
        },
        "max_worker_processes": {
            "apply_type": "static",
            "data_type": "integer",
            "min_val": 1,
            "max_val": 1024,
            "default": "8",
            "description": "Sets the maximum number of background processes that the system can support.",
        },
        "max_parallel_workers": {
            "apply_type": "dynamic",
            "data_type": "integer",
            "min_val": 0,
            "max_val": 1024,
            "default": "8",
            "description": "Sets the maximum number of parallel workers that the system can support.",
        },
        "max_parallel_workers_per_gather": {
            "apply_type": "dynamic",
            "data_type": "integer",
            "min_val": 0,
            "max_val": 1024,
            "default": "2",
            "description": "Sets the maximum number of workers that can be started by a single Gather node.",
        },
        "track_activities": {
            "apply_type": "dynamic",
            "data_type": "boolean",
            "allowed_values": ["on", "off"],
            "default": "on",
            "description": "Enables the collection of information on the currently executing command of each session.",
        },
        "track_counts": {
            "apply_type": "dynamic",
            "data_type": "boolean",
            "allowed_values": ["on", "off"],
            "default": "on",
            "description": "Enables collection of statistics on database activity.",
        },
        "log_min_duration_statement": {
            "apply_type": "dynamic",
            "data_type": "integer",
            "min_val": -1,
            "max_val": 2147483647,
            "default": "-1",
            "description": "Sets the minimum execution time above which statements will be logged.",
        },
        "statement_timeout": {
            "apply_type": "dynamic",
            "data_type": "integer",
            "min_val": 0,
            "max_val": 2147483647,
            "default": "0",
            "description": "Sets the maximum allowed execution time of any statement in milliseconds.",
        },
        "idle_in_transaction_session_timeout": {
            "apply_type": "dynamic",
            "data_type": "integer",
            "min_val": 0,
            "max_val": 2147483647,
            "default": "0",
            "description": "Sets the maximum allowed idle time in transaction in milliseconds.",
        },
        "password_encryption": {
            "apply_type": "dynamic",
            "data_type": "string",
            "allowed_values": ["scram-sha-256", "md5"],
            "default": "scram-sha-256",
            "description": "Sets the algorithm for encrypting passwords.",
        },
        "ssl": {
            "apply_type": "dynamic",
            "data_type": "boolean",
            "allowed_values": ["on", "off"],
            "default": "on",
            "description": "Enables SSL connections.",
        },
        "enable_seqscan": {
            "apply_type": "dynamic",
            "data_type": "boolean",
            "allowed_values": ["on", "off"],
            "default": "on",
            "description": "Enables the query planner's use of sequential scan plan types.",
        },
        "enable_indexscan": {
            "apply_type": "dynamic",
            "data_type": "boolean",
            "allowed_values": ["on", "off"],
            "default": "on",
            "description": "Enables the query planner's use of index scan plan types.",
        },
        "enable_hashjoin": {
            "apply_type": "dynamic",
            "data_type": "boolean",
            "allowed_values": ["on", "off"],
            "default": "on",
            "description": "Enables the query planner's use of hash-join plan types.",
        },
        "enable_mergejoin": {
            "apply_type": "dynamic",
            "data_type": "boolean",
            "allowed_values": ["on", "off"],
            "default": "on",
            "description": "Enables the query planner's use of merge-join plan types.",
        },
    }

    @classmethod
    def get_parameter_metadata(cls, param_name: str) -> Optional[Dict[str, Any]]:
        """Get parameter metadata by name."""
        return cls.POSTGRES_16_PARAMETERS.get(param_name)

    @classmethod
    def validate_parameter_value(cls, param_name: str, value: str) -> Tuple[bool, Optional[str]]:
        """Validate parameter value against catalog rules."""
        meta = cls.get_parameter_metadata(param_name)
        if not meta:
            return True, None

        allowed = meta.get("allowed_values")
        if allowed and str(value).lower() not in [str(a).lower() for a in allowed]:
            return False, f"Value '{value}' for {param_name} must be one of {allowed}"

        dtype = meta.get("data_type")
        if dtype == "integer":
            try:
                v = int(value)
                min_v = meta.get("min_val")
                max_v = meta.get("max_val")
                if min_v is not None and v < min_v:
                    return False, f"{param_name} value {v} below minimum {min_v}"
                if max_v is not None and v > max_v:
                    return False, f"{param_name} value {v} exceeds maximum {max_v}"
            except ValueError:
                return False, f"{param_name} must be an integer"
        elif dtype == "float":
            try:
                v = float(value)
                min_v = meta.get("min_val")
                max_v = meta.get("max_val")
                if min_v is not None and v < min_v:
                    return False, f"{param_name} value {v} below minimum {min_v}"
                if max_v is not None and v > max_v:
                    return False, f"{param_name} value {v} exceeds maximum {max_v}"
            except ValueError:
                return False, f"{param_name} must be a float"

        return True, None
