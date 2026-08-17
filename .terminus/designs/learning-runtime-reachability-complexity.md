# Learning Candidate — Runtime-Reachable Complexity

Status: `NON_AUTHORITATIVE_DESIGN_LEARNING`

Source task: `cobol-comp3-python-equiv`

Source observation date: `2026-08-17`

## Context

The completed COBOL inventory cutover task has a broad production-style module tree. Its core execution path is meaningfully connected (`cli` → orchestration → pipeline, with accounting, policy, checkpoint/replay, reconciliation, reporting, publication, journaling and operational workflows). The task is accepted as-is.

A post-completion architecture review also identified a useful future-task design lesson: raw source-file count and LOC are not sufficient evidence of realistic large-system complexity. Some modules can be technically substantive yet remain weakly connected, redundant with another implementation, or unreachable from a public/operator workflow.

This note is a future-design learning only. It is **not** a retroactive defect, finding, gate failure, or reopening of `cobol-comp3-python-equiv`.

## Future design rule candidate

For new large-system tasks, every substantive solver-visible production module should satisfy at least one of these conditions:

1. It is reachable from a documented public runtime entrypoint.
2. It is reachable from an operator/admin/maintenance workflow that is itself reachable.
3. It implements a migration, recovery, audit, or maintenance responsibility with a documented runtime consumer.
4. It is an intentionally extensible interface/adapter with a concrete documented consumer or extension boundary.

A substantive module that satisfies none of these should be treated as `ORPHAN_PRODUCTION_CODE` for design review and should not contribute to claimed task complexity merely because it increases file or LOC counts.

## Duplicate-domain rule candidate

When two production modules implement materially overlapping domain responsibilities, the task design should provide an architectural justification and a real consumer for each implementation.

Examples of the class of duplication to inspect:

- accounting engine vs. separate valuation engine;
- durable event journal vs. separate audit-chain implementation;
- primary inventory mutation path vs. a separate allocation/reservation subsystem.

If one implementation is not meaningfully consumed, prefer removal or explicit integration instead of retaining it as breadth-only scaffolding.

## Complexity measurement learning

Future strict complexity assessment should prefer **runtime-connected complexity** over raw structural volume.

Useful evidence includes:

- public/operator entrypoints;
- import/call reachability;
- durable state ownership;
- cross-module data/control flow;
- independently meaningful domain responsibilities;
- production workflows exercised by verifier/runtime evidence;
- justified extension boundaries.

Raw file count, alphabetically broad module naming, and LOC should remain supporting signals only and must not by themselves establish large-system authenticity.

## Review heuristic candidate

Before freezing a new large-system task, perform a lightweight production reachability inventory:

- list substantive production modules;
- identify their runtime/operator consumer;
- flag orphan modules;
- flag duplicate domain implementations;
- record justified exceptions;
- exclude unjustified orphan/redundant code from complexity claims.

This heuristic is intended for future task construction and production-authenticity review. Promotion into authoritative policy should follow the repository's normal learning/policy process rather than being inferred from this design note alone.
