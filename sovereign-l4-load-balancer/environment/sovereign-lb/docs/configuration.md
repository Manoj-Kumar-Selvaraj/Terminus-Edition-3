# Configuration

The desired document is complete replacement state, not a patch. Its top-level fields are `revision`, `listeners`, `target_groups`, `rollout`, and `limits`. Names are lowercase DNS-like identifiers up to 63 characters. Addresses are literal IPv4 or IPv6 addresses; listener and target ports are 1 through 65535.

Each listener has a unique `name` and unique `(address, port)` tuple, references one target group, and sets `proxy_protocol_v2`, `connect_timeout_ms`, `idle_timeout_ms`, and `buffer_bytes`. TCP is the only protocol.

Each target group has a unique name, balancing policy (`round_robin`, `least_connections`, or `source_hash`), zone policy (`cross_zone` or `same_zone_preferred`), explicit `fail_open`, health policy, drain timeout, and one or more targets.

Each target has a stable logical ID, address, port, zone, administrative state, weight, and incarnation. Removing then re-adding a logical target requires a larger incarnation. Runtime counters and connection ownership are keyed by group, target ID, and incarnation.

Active health policy defines interval, timeout, healthy threshold, unhealthy threshold, and optional send/expect byte strings with strict length limits. Passive policy defines failure window, failure threshold, and ejection duration. Administrative disable always excludes a target, including fail-open.

Rollout defines prepare and activate quorum as positive node counts, phase deadlines, and allowed unavailable zones. Quorum counts only connected current sessions that acknowledge the exact candidate generation and digest.

Limits cap listeners, groups, targets, frame bytes, queue messages, audit events, retained generations, health samples, connection records, and bytes buffered per direction. Values above implementation hard ceilings are invalid rather than silently clamped.

Canonical ordering sorts listeners and groups by name and targets by `(id, incarnation)`. Source hash uses the canonical eligible target identity order, so declaration order cannot change selection.