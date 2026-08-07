# freight-triage-polyglot-ledger-recovery

Human notes only. Agents never see this file.

## What the task is

Warehouse freight triage split across three languages that are supposed to share
one contract (`environment/docs/requirements.md`):

- `native/` — C++17 ledger CLI `freightctl`
- `intake/` — JDK-only Java 17 intake CLI `freight-intake`
- `reconcile/` — Go reconciler CLI `freight-reconcile`
- `data/` — registries, ~150 manifests, intake event log
- `bin/run-freight-suite` — builds all three and runs the pipeline

The stack ships broken. Eighteen source files disagree with the requirements
and with each other, so the ledger / journal / audit cannot be reconciled.
Goals live in `instruction.md`; schemas and algorithms live in the requirements
doc. The agent must repair sources — rewriting `/app/environment/data` to make
numbers match is cheating.

## Why it bites

Defects are correlated across languages. The freight epoch is wrong in C++ and
Go but right in Java; the seal digest is wrong in a different way in each
language. Fixing one side alone moves digests without making them agree.

Several bugs interact: slot allocation truncates kg to tonnes, ignores
priority, and emits zero-based indices. Those slots feed CSV sort order, lane
rollups and two digests. The corpus is large (~600 files); the signal is a
handful of one-line disagreements.

## Difficulty

Advanced. Roughly eighteen edits across C++/Java/Go with a build-and-diff loop
between them — well past five agent steps.

## Oracle

`solution/solve.sh` installs the eighteen fixed files from `solution/fixed/`
(same layout as `/app/environment`), clears build dirs, and runs
`/app/bin/run-freight-suite --root /app`. It never writes a golden document —
artifacts come from rebuilding the repaired sources.

## Verification

Separate verifier image (same three toolchains + pinned pytest). Suite embeds
an independent Python reference of the contract, rebuilds the agent's sources
through `run-freight-suite`, then grades artifacts: entry-by-entry snapshot,
canonical digests, byte-exact CSV, cross-language selftests, determinism
rerun, and a hand-built edge-case root. Hand-written outputs cannot pass.

## Base images / network

Both images use digest-pinned `python:3.13-slim-bookworm`. No single-language
canonical base covers g++ / JDK / Go together, so the Debian bookworm Python
image hosts all three toolchains. `network_mode = "no-network"` — sources,
data and Go module (`GOPROXY=off`) are baked in; Java is JDK-only.
