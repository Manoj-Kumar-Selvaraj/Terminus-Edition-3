"""Multi-tenant account, region, and tenant_id authorization projection."""
from typing import Any, Dict, List
from rds.errors import AuthorizationError

class AuthorizationEngine:
    """Enforces multi-tenant account, region, and tenant_id isolation."""

    @staticmethod
    def enforce_tenant_isolation(
        records: List[Dict[str, Any]],
        request_account_id: str,
        request_region: str,
        request_tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Filter records strictly matching request account, region, and tenant_id."""
        authorized = []
        for r in records:
            if (
                r.get("account_id") == request_account_id
                and r.get("region") == request_region
                and r.get("tenant_id") == request_tenant_id
            ):
                authorized.append(r)
        return authorized

    @staticmethod
    def authorize_single_instance(
        instance: Dict[str, Any],
        request_account_id: str,
        request_region: str,
        request_tenant_id: str
    ) -> Dict[str, Any]:
        """Authorize single instance access or raise AuthorizationError."""
        if (
            instance.get("account_id") != request_account_id
            or instance.get("region") != request_region
            or instance.get("tenant_id") != request_tenant_id
        ):
            raise AuthorizationError(
                f"Access denied: instance {instance.get('instance_id')} is not authorized for tenant {request_tenant_id}"
            )
        return instance
