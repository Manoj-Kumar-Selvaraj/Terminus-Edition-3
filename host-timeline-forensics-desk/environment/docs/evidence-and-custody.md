# Evidence and custody

Evidence bytes in the packaged environment are deterministic synthetic payloads. A content digest identifies bytes, not the case, source, endpoint, or acquisition history. Evidence metadata therefore retains those identities independently even when two items contain identical bytes.

An item distinguishes complete, partial, and unverifiable content. A digest over a prefix is not a complete-content verification. Before custody metadata becomes visible, the referenced object must be durable and its length/digest must agree with the manifest. Custody transfers, validation results, holds, and releases are append-only events with actor, reason, and timestamp.

Retention cannot remove objects referenced by an active case, hold, or published export. A rejected or untrusted observation can be retained as audit evidence but is not accepted evidence and must not appear as a verified timeline item.
