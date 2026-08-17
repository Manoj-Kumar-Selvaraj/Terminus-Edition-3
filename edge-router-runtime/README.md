# Edge Router Runtime

A Terminus Edition-3 systems task built around repairing a live Go HTTP edge-routing service. The starter is intentionally plausible: it compiles and serves traffic, but several individually reasonable implementation choices violate production semantics when routing, retry, reload, and shutdown behavior interact.

## Why this task is useful

The agent must reason about HTTP proxy behavior, host/path precedence, hop-by-hop headers, retry safety, atomic configuration publication, signal handling, and graceful connection draining. Verification is black-box: the tests build the submitted service, launch real local upstreams, mutate the documented configuration, and drive the process with real requests and Unix signals.

The verifier is designed to reject common partial fixes such as sorting routes once without respecting exact-host precedence, retrying every failed request, clearing the active config before parsing a reload, or terminating immediately on SIGTERM.

## Calibration

- Category: Software / Systems
- Language: Go
- Intended tier: advanced
- Agent-visible task stays concise; the detailed runtime semantics live in the product contract shipped with the starter code.
- No network access is required at runtime, although the task uses the repository default public network mode.
