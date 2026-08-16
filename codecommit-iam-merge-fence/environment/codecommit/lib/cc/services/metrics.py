from __future__ import annotations

from collections import Counter
from typing import Any

from cc.audit import query as audit_query
from cc.binding_index import coverage_report
from cc.branch_protection import summarize as protection_summary
from cc.ops_console import journal_by_pipeline, outbox_by_webhook, webhook_pending_summary
from cc.pipelines import event_id as eid
from cc.ref_lease import active_leases, purge_expired
from cc.webhooks import outbox


def snapshot() -> dict[str, Any]:
    purge_expired()
    audit = audit_query.summary()
    journal = eid.journal_rows()
    box = outbox.all_rows()
    pending = [r for r in box if r.get("status") in ("pending", "failed")]
    return {
        "audit": int(audit.get("total") or 0),
        "audit_denied": int(audit.get("denied") or 0),
        "journal_lines": len(journal),
        "pipelines": sorted({str(r.get("pipeline")) for r in journal}),
        "outbox_total": len(box),
        "outbox_pending": len(pending),
        "outbox_by_status": dict(Counter(str(r.get("status")) for r in box)),
        "bindings": coverage_report(),
        "protection": protection_summary(),
        "active_leases": len(active_leases()),
        "journal_by_pipeline": journal_by_pipeline(),
        "outbox_by_webhook": outbox_by_webhook(),
        "webhook_pending": webhook_pending_summary(),
    }
