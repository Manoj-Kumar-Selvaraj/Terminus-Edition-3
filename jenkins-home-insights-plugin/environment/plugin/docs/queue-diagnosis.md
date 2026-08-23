# Queue Diagnosis

Queue diagnosis is observational and never schedules, cancels, provisions, or relabels work. Each queue item is matched against one immutable node observation captured in the same reconciliation cycle.

Label expressions are conjunctions: every requested atom must be present. A normal node may accept unlabeled work and matching labeled work. An exclusive node accepts only explicitly matching work. Offline nodes and nodes refusing tasks contribute no available executors. Capacity distinguishes configured executors, busy executors, and currently available executors.

Blockage classes are runnable, label mismatch, no executor, offline, exclusive rejection, and cancelled. Cancelled items do not contribute demand. Pressure is active demand divided by usable configured capacity; an empty zero-capacity controller has zero pressure, while non-empty zero-capacity demand is unbounded.

Item age is measured against the reconciliation observation time, not wall-clock time during serialization. Stable observation time makes repeated output deterministic.
