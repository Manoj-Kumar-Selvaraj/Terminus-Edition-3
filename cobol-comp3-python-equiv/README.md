# Warehouse inventory cutover equivalence

This task contains an inherited Python runtime that replaces a legacy COBOL warehouse-movement cutover while preserving packed-decimal and record-layout semantics.

The runtime lives under `/app/equiv`. Operational evidence is available in `/app/equiv/log/archive` and `/app/equiv/ops`. The public CLI is `bin/equiv-eval`; use `--help` on the CLI and its subcommands for the supported interface.

The repair must preserve exact generation/restart semantics, inventory accounting, reconciliation and publication safety rather than merely decoding the sample layout.

<!-- temporary validation trigger -->
