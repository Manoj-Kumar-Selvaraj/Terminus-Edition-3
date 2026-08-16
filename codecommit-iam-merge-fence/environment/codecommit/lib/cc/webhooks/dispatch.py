from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from cc.webhooks import outbox, retry


def _post(url: str, payload: dict[str, Any], timeout: float = 2.0) -> tuple[bool, str | None]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= getattr(resp, "status", 200) < 300:
                return True, None
            return False, f"status={getattr(resp, 'status', '?')}"
    except urllib.error.URLError as exc:
        return False, str(exc)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def dispatch_pending(*, fixed: bool = False, sink: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Dispatch pending outbox rows. If sink is provided, record locally instead of HTTP."""
    results: list[dict[str, Any]] = []
    cfg = {w["id"]: w for w in outbox.load_webhook_config()}
    for row in outbox.pending():
        if not retry.should_retry(row, fixed=fixed) and fixed:
            # still attempt first pending
            if int(row.get("attempts") or 0) > 0 and row.get("status") == "failed":
                if not retry.should_retry(row, fixed=True):
                    continue
        wh = cfg.get(row.get("webhook_id"))
        if not wh:
            continue
        payload = {
            "event_id": row.get("event_id"),
            "repo": row.get("repo"),
            "ref": row.get("ref"),
            "commit": row.get("commit"),
            "pipeline": row.get("pipeline"),
        }
        if sink is not None:
            sink.append(payload)
            ok, err = True, None
        else:
            ok, err = _post(str(wh.get("url")), payload)
        updated = retry.mark_attempt(
            str(row.get("event_id")),
            str(row.get("webhook_id")),
            ok=ok,
            error=err,
            fixed=fixed,
        )
        results.append(updated)
    return results
