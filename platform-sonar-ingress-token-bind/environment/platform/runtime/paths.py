from __future__ import annotations

import os
from pathlib import Path


def root() -> Path:
    return Path(os.environ.get("PLATFORM_ROOT", "/app/platform"))


def stack_dir() -> Path:
    return root() / "stack"


def var_dir() -> Path:
    return root() / "var"


def ops_dir() -> Path:
    return root() / "ops"


def db_path() -> Path:
    return var_dir() / "platform.db"


def zone_path() -> Path:
    return var_dir() / "dns" / "zone.json"


def jenkins_home() -> Path:
    return var_dir() / "efs" / "jenkins-home"


def artifactory_data() -> Path:
    return var_dir() / "efs" / "artifactory-data"


def ssm_log() -> Path:
    return var_dir() / "ssm" / "commands.jsonl"


def desired_path() -> Path:
    return var_dir() / "desired.json"


def live_path() -> Path:
    return var_dir() / "live.json"
