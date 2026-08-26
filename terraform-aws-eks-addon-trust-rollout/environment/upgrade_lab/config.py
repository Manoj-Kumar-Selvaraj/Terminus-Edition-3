"""Configuration and environment settings for the EKS Add-on Trust Upgrade Lab."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _resolve_dir(env_key: str, default_str: str, relative_fallback: str) -> Path:
    if env_key in os.environ:
        return Path(os.environ[env_key])
    root = Path(__file__).resolve().parents[1]
    fallback = root / relative_fallback
    if not Path("/.dockerenv").exists() and fallback.is_dir():
        return fallback
    p = Path(default_str)
    if p.is_dir():
        return p
    if fallback.is_dir():
        return fallback
    return p


@dataclass
class LabConfig:
    """System configuration for upgrade lab execution."""

    data_dir: Path = field(
        default_factory=lambda: _resolve_dir("UPGRADE_DATA_DIR", "/app/data", "data")
    )
    var_dir: Path = field(
        default_factory=lambda: _resolve_dir("UPGRADE_VAR_DIR", "/app/var/upgrade", "var/upgrade")
    )
    output_dir: Path = field(
        default_factory=lambda: _resolve_dir("UPGRADE_OUTPUT_DIR", "/app/output", "output")
    )
    k8s_dir: Path = field(
        default_factory=lambda: _resolve_dir("UPGRADE_K8S_DIR", "/app/k8s", "k8s")
    )
    terraform_dir: Path = field(
        default_factory=lambda: _resolve_dir("UPGRADE_TF_DIR", "/app/terraform", "terraform")
    )
    workspace_dir: Path = field(
        default_factory=lambda: _resolve_dir("UPGRADE_WORKSPACE_DIR", "/app/terraform/workspaces/upgrade", "terraform/workspaces/upgrade")
    )
    account_id: str = "123456789012"
    cluster_name: str = "regulated-payments-eks"
    aws_region: str = "us-east-1"
    checkpoint_file: str = "checkpoint.json"
    telemetry_file: str = "telemetry_history.json"
    interruption_file: str = "interruption_events.json"

    def ensure_directories(self) -> None:
        """Ensure runtime directories exist."""
        self.var_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def plan_json_path(self) -> Path:
        """Path to regenerated plan.json."""
        return self.var_dir / "plan.json"

    @property
    def report_path(self) -> Path:
        """Path to output upgrade-report.json."""
        return self.output_dir / "upgrade-report.json"

    @property
    def checkpoint_path(self) -> Path:
        """Path to upgrade rollout state checkpoint."""
        return self.var_dir / self.checkpoint_file


def load_config() -> LabConfig:
    """Load and return current lab configuration."""
    cfg = LabConfig()
    cfg.ensure_directories()
    return cfg
