# Report Contract

Reports aggregate one fully committed scan generation. Dimensions are category, confidence band, source, department, region, policy, and remediation priority. Finding, suppressed, malformed, truncated, skipped, and terminal-failure states remain distinct.

JSON keys, arrays, CSV headers, rows, escaping, timestamps, and tie-breakers are deterministic. A manifest records schema version, tenant, job, scan generation, policy version and digest, corpus digest, completeness, counts by state, file names, byte lengths, and SHA-256 digests. The manifest digest excludes no semantic field.

Publication writes a new generation completely, verifies each file and digest, and only then atomically replaces `CURRENT`. Complete is never published while required work is partial or active.