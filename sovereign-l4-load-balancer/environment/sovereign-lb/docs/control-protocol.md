# Control protocol

The control channel is a persistent TCP stream. Every frame is a four-byte unsigned big-endian payload length followed by one UTF-8 canonical JSON object. The maximum frame length is configured and enforced before allocation. EOF within either prefix or body is a torn frame and has no state effect.

Canonical JSON uses UTF-8, sorted object keys, no insignificant whitespace, decimal integers, JSON booleans, and escaped strings. Floating-point values and duplicate object keys are forbidden. Digests are lowercase hexadecimal SHA-256 over the canonical snapshot object only.

## Envelope

Every message has `type`, `node_id`, `session_id`, `sequence`, and `sent_at`. Generation-bearing messages also have `generation` and `digest`. Unknown envelope fields are rejected. Message-specific bodies are under `body`.

`hello` opens a session and reports node identity, zone, software version, checkpoint generation, and capabilities. The control plane replies with the next appropriate `prepare` or requests status.

`prepare` carries one complete snapshot in `body.snapshot`. A node validates and durably checkpoints it without publishing listeners, then replies `prepared`. A node replies `rejected` with a stable reason code and bounded detail when validation fails.

`activate` names an already prepared generation and digest. A matching current session atomically publishes it and replies `active`. Activation without matching prepared state is rejected.

`status` is bidirectional and carries bounded readiness, active/prepared generation, listener count, connection count, and health summary. It never carries traffic payload or unbounded per-connection data.

Sequences begin at one for each new session and increase strictly. Duplicate messages with identical content produce the same response. Reuse of a sequence with different content, sequence regression, node mismatch, or stale session is rejected without advancing authority.

## Examples

```json
{"body":{"capabilities":["proxy-v2","checkpoint-v1"],"checkpoint_generation":41,"software":"0.1.0","zone":"zone-a"},"node_id":"dp-01","sent_at":"2026-01-01T00:00:00Z","sequence":1,"session_id":"dp-01-0001","type":"hello"}
```

```json
{"body":{"snapshot":{"generation":42,"listeners":[],"revision":17,"target_groups":[]}},"digest":"6d83b7f020b45e2584b6939e567176ef85888c8d80945a9f28d1bb9d0710eb29","generation":42,"node_id":"dp-01","sent_at":"2026-01-01T00:00:01Z","sequence":2,"session_id":"dp-01-0001","type":"prepare"}
```

```json
{"body":{},"digest":"6d83b7f020b45e2584b6939e567176ef85888c8d80945a9f28d1bb9d0710eb29","generation":42,"node_id":"dp-01","sent_at":"2026-01-01T00:00:02Z","sequence":3,"session_id":"dp-01-0001","type":"prepared"}
```

```json
{"body":{},"digest":"6d83b7f020b45e2584b6939e567176ef85888c8d80945a9f28d1bb9d0710eb29","generation":42,"node_id":"dp-01","sent_at":"2026-01-01T00:00:03Z","sequence":4,"session_id":"dp-01-0001","type":"activate"}
```

```json
{"body":{"listener_count":2,"ready":true},"digest":"6d83b7f020b45e2584b6939e567176ef85888c8d80945a9f28d1bb9d0710eb29","generation":42,"node_id":"dp-01","sent_at":"2026-01-01T00:00:04Z","sequence":5,"session_id":"dp-01-0001","type":"active"}
```

```json
{"body":{"code":"snapshot_invalid","detail":"listener address is not unique"},"digest":"6d83b7f020b45e2584b6939e567176ef85888c8d80945a9f28d1bb9d0710eb29","generation":42,"node_id":"dp-01","sent_at":"2026-01-01T00:00:04Z","sequence":5,"session_id":"dp-01-0001","type":"rejected"}
```