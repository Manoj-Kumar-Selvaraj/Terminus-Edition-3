* The freight ledger, intake journal, and audit under /app/environment no longer reconcile.
* Three tools disagree on the same books: C++ freightctl, Java freight-intake, and Go freight-reconcile.
* Fix them against the shared contract. Do not edit /app/environment/data/ to make the totals agree.

Shared
* All three share one freight epoch and dock-window length. Arrival timestamps include a UTC offset — apply it when calculating arrival_epoch_s. The wall clock is not already UTC.
* Normalize seals by trimming and upper-casing, then hash with CRC-32/ISO-HDLC into eight lowercase hex digits in natural byte order. 
* Write lowercase SHA-256 digests over the contract's canonical streams. Production artifacts must agree across languages, not just the self-tests.
* Keep artifacts deterministic: UTF-8, LF endings, stable JSON. Keep known-answer checksum families aligned. freightctl inspect and version output must follow the shared timestamp and seal rules.

freightctl
* Emit one ledger row for every manifest file, including empty ones. Slots start at one. Capacity is in kilograms. Priority settles contention. Tariff bands include their lower bound.

freight-intake
* Replay events by seq. Store hold rows by manifest_id and order them by that field. Count each accepted hold once.

freight-reconcile
* Match both upstream digests. Use half-open windows. Count orphan holds and lane/window totals without duplicating boundary arrivals. Round accrued cents half-up.
* Write the CSV with the required columns and LF endings. Keep the C++, Java, and Go self-test digests identical.

Suite / outputs
* Run /app/bin/run-freight-suite --root /app. It builds the stack and writes under /app/output: ledger-snapshot.json, intake-journal.json, audit-report.json, audit-ledger.csv, the three selftest-*.json files, and suite-manifest.json.
* The suite manifest must index every generated file accurately.

Contract
* /app/environment/docs/requirements.md defines constants, states, rejection codes, fields, digest streams, CSV columns, and self-test families. /app/environment/docs/layout.md covers the layout.
* Follow both. Do not weaken the algorithms or rewrite the docs to fit the current programs.
