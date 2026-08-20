# Operations

Operators provide policy, scanner fixtures, exception data, state directory, secret material, and optional RFC3339 time through the stable CLI. `evaluate` returns exit 42 on policy denial and 2 on operational failure. `verify-permit` returns exit 43 for an invalid permit. Production repair must fail closed on stale or unavailable scanner evidence, preserve durable audit history, and prevent permit replay across restart and concurrency boundaries.
