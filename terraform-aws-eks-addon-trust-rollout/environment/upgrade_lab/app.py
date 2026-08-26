"""Application coordinator and top-level entrypoint for the upgrade lab."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from upgrade_lab.config import LabConfig, load_config
from upgrade_lab.rollout_coordinator import execute_rollout


def run_rollout_app(
    plan: Dict[str, Any],
    cfg: Optional[LabConfig] = None,
    fail_addon: Optional[str] = None,
) -> Dict[str, Any]:
    """High-level application coordinator entrypoint for upgrade rollout execution."""
    config = cfg or load_config()
    return execute_rollout(plan, config, fail_addon=fail_addon)
