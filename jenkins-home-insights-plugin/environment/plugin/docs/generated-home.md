# Generated Home

The generator creates a sanitized export under `exports/` with nested jobs, build history, queued tasks, node capacity, fingerprints, plugin metadata, a capability record, and an inventory summary. The default population is 14,536 primary records and remains within the supported 10,000 to 20,000 range.

Variation is deterministic from the configured seed. Jobs span folders, repeated leaf names, labels, and lifecycle states. Builds span outcomes, running state, durations, artifacts, and history depth. Queue items combine labels, ages, cancellation, and blockage text. Nodes combine labels, modes, executor occupancy, offline state, and task acceptance. Fingerprints include multiple consumers and missing producers. Plugins include lifecycle, compatibility, dependency, bundled, and restart state.

Sparse malformed rows exercise per-record isolation. Capability metadata distinguishes unsupported fingerprint enumeration from an empty inventory. No credentials, tokens, user content, build logs, or external URLs are generated.

`inventory.json` records counts and a content digest. Re-running with the same seed and record count yields equivalent source content. Generated state is derived during image construction or explicit operator use and is not maintained as thousands of repository files.
