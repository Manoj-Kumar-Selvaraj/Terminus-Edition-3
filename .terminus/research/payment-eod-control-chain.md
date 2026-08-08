# Payment EOD task provenance / originality notes

The scenario is a synthetic but domain-grounded legacy batch incident: a COBOL decision chain plus shell orchestration and SQL durable state has unsafe restart behavior after internal postings or external reservations. The distinctive topology is the interaction between source-reference replay control, payer capacity, authoritative partial financial effects, clearing, four-row ledger obligations, cycle-scoped reconciliation, publication and a later completion authorization.

Public calibration reviewed before the redesign included Terminal-Bench payment, database cutover and dedup-style tasks as well as real engineering issue-writing samples. No reviewed task used this COBOL/shell/SQLite EOD restart topology. The design intentionally avoids copying requirement ordering, verifier topology or solution shape from a public benchmark.

Authenticity risk to watch: an exhaustive contract/test mapping can look benchmark-generated. Mitigation is to keep `instruction.md` incident-first and concise, keep technical details in ordinary operator/interface notes, cluster 29 defect manifestations under six operational root causes, and avoid one independent planted typo per test.
