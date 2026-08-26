"""Configuration management for Sovereign RDS Control Plane."""
import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings

class RDSConfig(BaseSettings):
    """Main control plane configuration."""

    database_url: str = Field(
        default="postgresql://rds_admin:rds_local_secret@localhost:5432/rds_control_plane",
        alias="DATABASE_URL"
    )

    state_dir: str = Field(default="/app/rds/state")
    output_dir: str = Field(default="/app/rds/out")

    default_region: str = Field(default="us-east-1")
    max_allowed_lag_bytes: int = Field(default=10485760)  # 10 MB
    failover_lease_ttl_sec: int = Field(default=15)
    health_probe_timeout_sec: int = Field(default=3)
    max_event_retries: int = Field(default=5)
    outbox_poll_interval_sec: int = Field(default=5)

    class Config:
        env_file = ".env"

def load_config() -> RDSConfig:
    """Load configuration from environment."""
    cfg = RDSConfig()
    Path(cfg.state_dir).mkdir(parents=True, exist_ok=True)
    Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)
    return cfg
