# Authorization

Operational insight access requires Jenkins overall read and the plugin's system-read capability. Item-backed records additionally require read access to their owning item. Jobs own themselves; builds are owned by their job; queue items are owned by their task. Lineage is visible only when every disclosed endpoint is visible.

Authorization is a projection over the captured generation. Filtering, correlation, aggregate computation, facet counts, totals, sorting, cursor positioning, and page slicing operate on that projection. This prevents inaccessible records from affecting observable counts, topology, ordering, or pagination.

Node and plugin inventory are controller-level data and require system access. Source errors inherit the visibility of the source record where one is identifiable. Errors that cannot be associated with a visible item are available only to administrators.

The standalone principal flags are deterministic substitutes for Jenkins ACL checks. They exist for operations and offline diagnosis; they do not persist credentials or grant Jenkins permissions.
