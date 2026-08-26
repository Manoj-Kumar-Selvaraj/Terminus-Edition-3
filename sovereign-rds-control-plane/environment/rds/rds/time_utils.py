"""UTC datetime utilities for Sovereign RDS Control Plane."""
from datetime import datetime, timezone

def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)

def format_utc(dt: datetime) -> str:
    """Format datetime as ISO 8601 UTC string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def parse_utc(iso_str: str) -> datetime:
    """Parse ISO 8601 UTC string into datetime."""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
