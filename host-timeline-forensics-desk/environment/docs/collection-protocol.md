# Collection protocol

Live and offline acquisition requests share a case/source identity model but have source-specific capability and delivery contracts. A live request is addressed only to the local collection lab in this environment. An offline bundle is self-contained and carries endpoint, case, source, plan, item, attempt, capture time, and manifest metadata.

The worker claims bounded work under an expiring lease. A logical collection item has monotonically increasing attempt identities; a stale worker or delayed callback cannot become authoritative after a newer attempt is active. An acknowledgement that is ambiguous must be reconciled with the lab's known run identity before another logical collection is issued.

Callbacks are signed over the exact raw request bytes before JSON interpretation. Delivery identity is immutable: repeating an identical delivery is idempotent; reusing its identity for another payload is a conflict. Every accepted event binds to the active case, endpoint, collection item, source, and attempt. Progress reduces monotonically, and terminal state does not regress.
