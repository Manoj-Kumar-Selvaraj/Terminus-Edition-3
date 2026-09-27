# Reporting and export

Coverage is derived from the immutable set of requested sources and their explicit terminal dispositions, not just from evidence rows. A case timeline orders accepted items by normalized UTC capture time with stable source and evidence identifiers, while retaining source-time and quality/provenance traits.

Exports read one authorized case snapshot and include a stable manifest version, case and plan identities, ordered source dispositions, evidence identities, complete digests, custody references, and a deterministic SHA-256. Authorization applies before row counts, facets, timeline details, custody events, or export bytes are exposed. Repeated export of unchanged committed state produces identical manifest bytes.
