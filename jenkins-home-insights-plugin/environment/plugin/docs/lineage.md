# Artifact Lineage

Fingerprints connect one producer build to zero or more consumer builds. Build keys connect those endpoints to jobs. A retained fingerprint can outlive either endpoint; missing producer and consumer states therefore remain explicit rather than deleting the edge.

Job display-name changes do not alter endpoint identity. Deleted jobs and builds may be retained as tombstones for the configured number of cycles when a retained fingerprint still references them. Compaction first determines the live reference closure and then chooses removable generations and tombstones.

Lineage output includes fingerprint key, producer build key, consumer build key, resolved job keys, and missing-endpoint flags. Duplicate event delivery must not multiply an edge. Cycles are reported as diagnostics and do not mutate the graph.

Authorization applies to both endpoints before an edge is visible. Redacting an endpoint label while retaining edge existence or multiplicity is not an authorized projection.
