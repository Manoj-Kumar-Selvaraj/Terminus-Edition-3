from __future__ import annotations


def session_key(tenant_id: str, user_id: str) -> tuple[str, str]:
    return (str(tenant_id), str(user_id))
