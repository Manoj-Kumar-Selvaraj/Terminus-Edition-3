"""Mock AWS EKS, IAM, and SSM API protocol simulator for local offline execution."""
from __future__ import annotations

import uuid
from typing import Any, Dict


class MockAWSLab:
    """Offline protocol lab simulator for AWS EKS add-ons, IAM roles, and SSM parameter store."""

    def __init__(self, account_id: str = "123456789012", region: str = "us-east-1"):
        self.account_id = account_id
        self.region = region
        self.roles: Dict[str, Dict[str, Any]] = {}
        self.addons: Dict[str, Dict[str, Any]] = {}
        self.ssm_parameters: Dict[str, Dict[str, Any]] = {}

    def describe_addon(self, cluster_name: str, addon_name: str) -> Dict[str, Any]:
        """Simulate EKS DescribeAddon API call."""
        addon = self.addons.get(addon_name)
        if not addon:
            return {
                "addon": {
                    "addonName": addon_name,
                    "status": "NOT_INSTALLED",
                    "addonVersion": None,
                }
            }
        return {"addon": addon}

    def update_addon(
        self, cluster_name: str, addon_name: str, addon_version: str, resolve_conflicts: str
    ) -> Dict[str, Any]:
        """Simulate EKS UpdateAddon API call."""
        addon = {
            "addonName": addon_name,
            "status": "ACTIVE",
            "addonVersion": addon_version,
            "resolveConflicts": resolve_conflicts,
        }
        self.addons[addon_name] = addon
        return {"addon": addon}

    def get_role(self, role_name: str) -> Dict[str, Any]:
        """Simulate IAM GetRole API call."""
        role = self.roles.get(role_name)
        if not role:
            return {}
        return {"Role": role}

    def get_parameter(self, name: str) -> Dict[str, Any]:
        """Simulate SSM GetParameter API call."""
        param = self.ssm_parameters.get(name)
        if not param:
            return {}
        return {"Parameter": param}
