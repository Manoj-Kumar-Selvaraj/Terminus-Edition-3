from __future__ import annotations

from typing import Any

from cc.pipelines import event_id as eid_mod
from cc.repos import gitops
from cc.util import full_ref


def deliver(repo: str, ref: str, *, fixed: bool = False) -> dict[str, Any]:
    normalize = fixed
    # Broken starter: no normalization for binding lookup
    bindings = eid_mod.bindings_for(repo, ref, normalize=normalize)
    if not bindings:
        return {"ok": True, "delivered": [], "duplicate": False}

    tip = gitops.ref_commit(repo, full_ref(ref))

    delivered: list[dict[str, Any]] = []
    all_dup = True
    for b in bindings:
        pipeline = str(b.get("pipeline"))
        ref_n = full_ref(ref)
        event_id = eid_mod.event_id(repo, ref_n, tip, pipeline, fixed=fixed)
        already = eid_mod.has_event(event_id) if fixed else False
        # Broken: never treat as duplicate; always append
        if fixed and already:
            delivered.append(
                {
                    "event_id": event_id,
                    "repo": repo,
                    "ref": ref_n,
                    "commit": tip,
                    "pipeline": pipeline,
                    "status": "delivered",
                }
            )
            continue
        all_dup = False
        row = {
            "event_id": event_id,
            "repo": repo,
            "ref": ref_n,
            "commit": tip,
            "pipeline": pipeline,
            "status": "delivered",
        }
        eid_mod.append_delivery(row, fixed=fixed)
        delivered.append(row)
        if fixed:
            from cc.webhooks.outbox import enqueue_for_delivery

            enqueue_for_delivery(row)
        # Broken: skip outbox enqueue

    return {"ok": True, "delivered": delivered, "duplicate": bool(fixed and all_dup and delivered)}
