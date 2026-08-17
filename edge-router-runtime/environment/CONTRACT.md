# Runtime contract

The program is a single-process HTTP edge router. It starts the public listener from `listen` and the admin listener from `admin_listen` in `/app/edge-router/config.json`. Startup must fail before serving if the config is invalid.

A route matches when both its host rule and `path_prefix` match. Host comparison is case-insensitive and ignores a request Host port. A literal host outranks every wildcard match. A wildcard of the form `*.example.test` matches subdomains only, not `example.test`. Within the winning host class choose the longest matching path prefix; preserve config order only as the final tie-break. Each route requires at least one absolute `http` or `https` upstream URL.

Proxy the original method, path, query and body. Preserve the original Host header. Remove standard hop-by-hop headers and every header named by the request `Connection` header before forwarding. Append the client address to an existing `X-Forwarded-For` chain, set `X-Forwarded-Host` to the original Host value, and set `X-Forwarded-Proto` to `http`. Strip hop-by-hop headers from upstream responses too.

Upstreams are selected round-robin independently per route. A transport failure may be retried once, against the next upstream, only for `GET`, `HEAD`, and `OPTIONS`; methods with a request body must never be replayed. An upstream HTTP status is a response, not a transport failure, and must never trigger a retry. If no upstream returns a response, return 502.

`GET /_edge/health` on the admin listener returns JSON with `status: "ok"` and the currently active config `generation`. `GET /_edge/config` returns JSON containing the active `generation` and `route_count`. Other admin paths return 404.

On `SIGHUP`, reread `/app/edge-router/config.json`. A valid reload becomes visible atomically to new requests and increments `generation` by exactly one. Existing in-flight requests continue with the snapshot they started with. Listener addresses are immutable after startup; changing either listener makes a reload invalid. Any invalid reload must leave the previous snapshot and generation untouched while the process keeps serving.

On `SIGTERM` or `SIGINT`, stop accepting new public and admin connections, allow in-flight requests to finish for up to `shutdown_timeout_ms`, then exit. The process must not terminate an in-flight request immediately when graceful shutdown begins.
