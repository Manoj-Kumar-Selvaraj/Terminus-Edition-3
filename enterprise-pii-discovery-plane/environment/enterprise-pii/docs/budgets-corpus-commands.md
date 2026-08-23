# Budgets, Corpus, and Commands

Budget exhaustion is explicit, deterministic, bounded, and resumable where the format permits. Metrics use a fixed label vocabulary and bounded series. Audit is a bounded sequence with overflow accounting. Readiness is false until recovery completes, required configured sources are available, and enough current compatible workers have heartbeated.

`generate-corpus --output DIR --records 12000` deterministically replaces only its managed output and emits exactly 12,000 synthetic records plus a manifest. Departments are HR, finance, legal, support, sales, engineering, and vendor; regions are NA, EU, and APAC. Inputs include clean controls, valid and invalid candidates, governed repeats, malformed records, and every supported format. Personas are algorithmic and explicitly synthetic.

`pii-control serve|recover|status` hosts or inspects the service. `piictl policy publish`, `source list`, `job create|cancel|status`, `worker list`, `report show|export`, `health`, and `metrics` call the same HTTP-independent service layer used by the API. Commands provide JSON by default, stable exit codes, and no network dependency beyond the local control endpoint.