# State Model

Canonical records have a source family, stable key, display attributes, observed sequence, and family-specific fields. Display names and URLs are presentation data. Keys are used by build ownership, queue tasks, lineage endpoints, events, ACL decisions, and pagination.

Record states distinguish active, running, cancelled, deleted, malformed, and unsupported material. Source errors are records in their own right: an invalid source item does not erase valid adjacent items. Unsupported enumeration is distinct from a supported empty source.

The event sequence is monotonic within one state directory. An event contains an identity, source family, operation, record key, payload digest, and payload. Event identities are globally unique. Repeated identical events are idempotent; a reused identity with another payload is a conflict. Deletes fence older upserts for the same record.

A checkpoint names the highest contiguous event represented by a generation. It advances only after reduction and publication succeed. Replay begins strictly after the selected generation checkpoint.

Snapshots are immutable values. Full scans replace each successfully captured source family. Incremental batches apply ordered transitions. Equivalent source state must serialize to the same canonical digest regardless of entry path.
