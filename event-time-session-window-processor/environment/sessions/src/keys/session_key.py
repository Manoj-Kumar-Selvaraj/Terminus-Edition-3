from __future__ import annotations


def session_key(tenant_id: str, user_id: str) -> tuple[str, str]:
    _ = tenant_id
    return ("*", str(user_id))
