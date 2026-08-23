# Authorization Contract

Principals receive explicit tenant, department, region, source, and action grants. Deny by default. Authorization is applied to the candidate source set before reading findings or computing any derivative.

Rows, examples, dedupe groups, counts, facets, totals, cursors, pagination boundaries, report manifests, JSON exports, and CSV exports operate only on the authorized projection. A cursor binds principal, grants digest, report generation, query, and sort order. Reusing it after any of those change is rejected.

The API and CLI invoke the same service methods. Error differences, timing metadata, existence checks, and audit events must not reveal hidden source identities or counts.