# State format

`cache/<key>.json` stores scan evidence, `audit.jsonl` stores decision journal records, `last-decision.json` is a derived projection, and `replay/consumed.jsonl` records permit consumption. State transitions are intended to be crash-safe and replay-safe, but the starter contains deliberate defects in cache identity, durability ordering, malformed-tail recovery, locking, and replay atomicity.
