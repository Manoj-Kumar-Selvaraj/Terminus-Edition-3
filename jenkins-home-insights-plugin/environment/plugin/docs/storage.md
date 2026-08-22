# Storage

Derived state lives under the configured state directory:

```
CURRENT
journal/events.ndjson
generations/gen-*/manifest.json
generations/gen-*/jobs.json
generations/gen-*/builds.json
generations/gen-*/queues.json
generations/gen-*/nodes.json
generations/gen-*/fingerprints.json
generations/gen-*/plugins.json
generations/gen-*/errors.json
generations/gen-*/analysis.json
generations/gen-*/checkpoint.json
leases/*.lease
```

Publication writes a staging generation, fsyncs durable content, verifies every checksum, validates schema and references, atomically renames the directory, and finally atomically replaces `CURRENT`. Readers retain a generation lease for the duration of a query.

Startup validates the pointed generation and all complete unpointed candidates. Selection is deterministic and falls back from incomplete, corrupt, mixed-schema, or out-of-bounds generations. Journal replay starts after the selected checkpoint. A torn final journal record is isolated without discarding the valid prefix.

Migration never edits an active generation. It reads the old schema and publishes a new current-schema generation. Retention preserves `CURRENT`, leased generations, recovery fallback, and referenced tombstones.
