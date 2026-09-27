# Case, identity, and policy model

A tenant owns cases and endpoints. A case has a stable identifier, owner scope, revision, lifecycle state, and zero or more active holds. Actors receive case-scoped permissions. Authorization is evaluated before case metadata, counts, coverage, timeline rows, custody, or export information is read.

Endpoint inventory is generation-scoped. Each endpoint reports a platform, site, lifecycle state, and supported acquisition source families. A plan binds a case revision, policy revision, inventory generation, actor, source mode, requested source families, resource limits, and deadlines. Policy revisions and submitted plans are immutable; changing policy or requested scope creates a distinct plan identity.

The system distinguishes absent policy configuration from an explicit empty grant. A missing authority is not permission. Cross-tenant endpoint IDs and repeated display aliases do not establish ownership; the tenant/case relationship remains authoritative.
