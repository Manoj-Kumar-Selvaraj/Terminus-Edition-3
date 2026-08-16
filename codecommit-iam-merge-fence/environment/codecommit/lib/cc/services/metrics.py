from __future__ import annotations
from collections import Counter
from typing import Any
from cc.audit import query as audit_query
from cc.webhooks import outbox
from cc.pipelines import event_id as eid

def snapshot() -> dict[str, Any]:
    audit = audit_query.summary()
    journal = eid.journal_rows()
    box = outbox.all_rows()
    return {
        'audit': audit,
        'journal_lines': len(journal),
        'pipelines': sorted({str(r.get('pipeline')) for r in journal}),
        'outbox_total': len(box),
        'outbox_by_status': dict(Counter(str(r.get('status')) for r in box)),
    }
