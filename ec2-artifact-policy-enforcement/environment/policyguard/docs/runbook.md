# PolicyGuard operator contract

PolicyGuard is the host-side admission point used before managed EC2 software ingress. `policyguard evaluate` is the common decision engine. The three wrappers under `bin/` add the artifact kind and otherwise forward the same request fields.

Required request fields are `--name`, `--version`, `--source`, `--digest`, `--instance`, `--environment`, and `--now`. Container callers also pass `--signed true|false`. Scanner outages can be represented by `--scanner-status unavailable`; normal operation reads `config/scan-db.tsv`, which stands in for the normalized result returned by the production Trivy adapter. A digest absent from the scanner database is unknown evidence, not a clean result.

The policy file defines the policy generation, scanner database generation, blocking severity, trusted source sets, container requirements, cache TTL, fail-closed posture, and permit TTL. Exit `0` means ALLOW, `42` means DENY, and the final stdout line is a JSON decision containing `decision`, `reason`, `artifact`, policy/scanner generations, cache status, optional exception ID, and optional permit. `verify-permit` returns exit `0` only for a permit valid for the supplied instance, digest, and time.

Persistent state lives under `state/`. `cache.tsv` is an implementation detail and may be rebuilt, but a cached result is valid only for the same immutable artifact and policy/scanner generations and within its TTL. `audit.jsonl` is append-only operational evidence and must survive process restarts. Do not truncate it during repair. Security exceptions in `config/exceptions.tsv` are vulnerability waivers only; source trust, immutable identity, required scan evidence, and container signature requirements are not waivable.
