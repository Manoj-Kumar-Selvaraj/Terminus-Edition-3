# Golden Task Reference Registry

These are reference tasks from the public `harbor-framework/terminal-bench` repository. They are not templates and must not be copied structurally or textually. Use them to calibrate task quality, realism, verifier depth, and explanation style.

Pinned source commit for the current registry:

`adc34389da1a7c353788fb3854bce7938bd685d5`

The upstream repository identifies Terminal-Bench as a benchmark for measuring agents' ability to complete terminal tasks and keeps tasks under `tasks/`. Review references at the pinned commit so later upstream changes do not silently change our calibration set.

## Software / systems references

### `wal-recovery-ordering`

Why keep it:
- realistic multi-stage storage/recovery failure topology;
- observable invariants rather than naming buggy modules;
- coupled bugs where partial fixes remain incorrect;
- broad semantic pytest coverage plus determinism and performance checks.

Use it to calibrate:
- multi-component reasoning depth;
- restart/recovery semantics;
- verifier breadth without implementation-pattern grading.

Do not copy:
- WAL/recovery scenario;
- its specific five-stage structure;
- test names, wording, or recovery invariants.

Source: `tasks/wal-recovery-ordering/` at the pinned upstream commit.

### `mvcc-lsm-compaction`

Why keep it:
- root cause is a visibility/invariant problem rather than a local syntax defect;
- solver must reason across MVCC publication, flush, and compaction semantics;
- verifier includes independent hidden harnesses and a reference model;
- rejects the trivial "retain everything" workaround with a storage-budget behavior test.

Use it to calibrate:
- hard-but-fair hidden-state interactions;
- anti-shortcut verifier design;
- realistic partial-state concurrency reasoning.

Do not copy:
- MVCC/LSM scenario;
- RocksDB-like concepts or exact hidden-harness pattern;
- its wording or solution topology.

Source: `tasks/mvcc-lsm-compaction/` at the pinned upstream commit.

## Cross-domain references to add deliberately

The registry should eventually contain a small set across categories, for example Hardware/CAD, Science, Operations, and Security. Add a task only after manually reviewing its instruction, task.toml, environment, solution, and verifier. Record why it is worth preserving. Do not bulk-import upstream tasks.

## Reference review checklist

Before adding a golden task:

1. Pin the upstream commit.
2. Read `instruction.md`, `task.toml`, environment, solution, tests, and README.
3. Confirm the task demonstrates at least one quality we want to calibrate.
4. Record both what to learn and what must not be copied.
5. Prefer diversity of failure topology over many examples from one domain.
6. Never treat an upstream example as higher priority than current Edition 3 enforcement/rules.
