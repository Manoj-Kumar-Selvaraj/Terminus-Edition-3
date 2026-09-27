"""Typed service configuration with safe local defaults."""
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FORENSIC_", extra="ignore")

    database_url: str = Field(
        default="postgresql://forensics:local-forensics-only@localhost:5432/forensics",
        alias="DATABASE_URL",
    )
    lab_url: str = Field(default="http://127.0.0.1:8091", alias="LAB_URL")
    evidence_root: Path = Field(default=Path("/app/state/evidence"), alias="EVIDENCE_ROOT")
    output_dir: Path = Field(default=Path("/app/out"), alias="OUTPUT_DIR")
    worker_id: str = Field(default="worker-local", alias="WORKER_ID")
    worker_lease_seconds: int = Field(default=45, ge=5, le=600)
    worker_batch_size: int = Field(default=24, ge=1, le=200)
    max_callback_bytes: int = Field(default=1_048_576, ge=1024, le=16_777_216)
    callback_secret: str = Field(default="synthetic-lab-callback-key", alias="CALLBACK_SECRET")
    max_clock_skew_seconds: int = Field(default=600, ge=0, le=86_400)
    default_case_budget_bytes: int = Field(default=536_870_912, ge=1)
    lab_seed: str = Field(default="sha256-deterministic-v1", alias="LAB_SEED")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("worker_id")
    @classmethod
    def worker_id_is_nonempty(cls, value: str) -> str:
        rendered = value.strip()
        if not rendered:
            raise ValueError("worker_id must not be empty")
        return rendered

    @field_validator("database_url", "lab_url")
    @classmethod
    def service_url_is_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("service URL must not be empty")
        return value.strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable configuration snapshot."""
    return Settings()
