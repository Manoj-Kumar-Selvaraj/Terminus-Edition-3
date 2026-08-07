# Golden Task Reference Registry

These are reference tasks from the public `harbor-framework/terminal-bench` repository. They are not templates and must not be copied structurally or textually. Use them to calibrate realism, task diversity, verifier depth, difficulty topology, and explanation style.

Pinned upstream commit:

`adc34389da1a7c353788fb3854bce7938bd685d5`

Always inspect references at that exact commit so upstream changes do not silently alter our calibration set. Current Edition 3 enforcement/rules remain higher priority than any reference task.

## Reference policy

- Keep 20–30 diverse references available; current catalog contains **25**.
- Prefer diversity of domain and failure topology over many similar tasks.
- Before borrowing a design principle, inspect the task's `instruction.md`, `task.toml`, environment, solution, tests, and README.
- Learn patterns such as realism, invariant depth, and verifier strategy. Never copy wording, test names, task structure, scenario, constants, or solution topology.
- A reference can demonstrate one useful quality without being a perfect model for every current Edition 3 rule.

## Catalog: 25 pinned references

| # | Upstream task | Reference area | Pinned source |
| ---: | --- | --- | --- |
| 1 | `wal-recovery-ordering` | storage/recovery, coupled invariants, concurrency | `tasks/wal-recovery-ordering/` |
| 2 | `mvcc-lsm-compaction` | databases, MVCC/LSM state interaction | `tasks/mvcc-lsm-compaction/` |
| 3 | `cad-model` | CAD / artifact construction | `tasks/cad-model/` |
| 4 | `wdm-design` | engineering/design optimization | `tasks/wdm-design/` |
| 5 | `uefi-bootkit` | security / low-level systems | `tasks/uefi-bootkit/` |
| 6 | `shadow-relay` | networking / systems behavior | `tasks/shadow-relay/` |
| 7 | `exam-pdf-eval` | document/evaluation workflow | `tasks/exam-pdf-eval/` |
| 8 | `gpt2-codegolf` | constrained programming / optimization | `tasks/gpt2-codegolf/` |
| 9 | `formal-crypto` | cryptography / formal reasoning | `tasks/formal-crypto/` |
| 10 | `lake-temp-glm` | scientific modeling / data analysis | `tasks/lake-temp-glm/` |
| 11 | `music-harmony` | media/music reasoning | `tasks/music-harmony/` |
| 12 | `ks-solver-cpp` | numerical/scientific C++ | `tasks/ks-solver-cpp/` |
| 13 | `fin-saccr-rwa` | finance / regulatory calculation | `tasks/fin-saccr-rwa/` |
| 14 | `ico-path-patch` | software artifact/path repair | `tasks/ico-path-patch/` |
| 15 | `html-js-filter` | frontend / browser behavior | `tasks/html-js-filter/` |
| 16 | `gsea-proteomics` | biology / scientific data analysis | `tasks/gsea-proteomics/` |
| 17 | `kv-live-surgery` | live systems / key-value state repair | `tasks/kv-live-surgery/` |
| 18 | `atrx-vep-crispr` | biology / genomics workflow | `tasks/atrx-vep-crispr/` |
| 19 | `coq-block-bound` | formal proof / theorem proving | `tasks/coq-block-bound/` |
| 20 | `react-lead-form` | frontend / application behavior | `tasks/react-lead-form/` |
| 21 | `cli-2ph-simplex` | math / CLI algorithm implementation | `tasks/cli-2ph-simplex/` |
| 22 | `fp8-rmsnorm-gemm` | ML kernels / performance correctness | `tasks/fp8-rmsnorm-gemm/` |
| 23 | `math-eval-grader` | evaluation / grading semantics | `tasks/math-eval-grader/` |
| 24 | `rs-archive-clone` | systems / archive behavior | `tasks/rs-archive-clone/` |
| 25 | `freecad-impeller` | CAD / geometric artifact verification | `tasks/freecad-impeller/` |

All paths above are in `harbor-framework/terminal-bench` at the pinned commit.

## Deep-reference notes

### `wal-recovery-ordering`

Why keep it:
- realistic multi-stage storage/recovery failure topology;
- observable invariants rather than naming buggy modules;
- coupled bugs where partial fixes remain incorrect;
- broad semantic pytest coverage plus determinism/performance considerations.

Use it to calibrate multi-component reasoning depth, restart/recovery semantics, and verifier breadth without implementation-pattern grading.

Do not copy its WAL scenario, stage structure, wording, test names, or recovery invariants.

### `mvcc-lsm-compaction`

Why keep it:
- root cause is a visibility/invariant problem rather than a local syntax defect;
- reasoning spans publication, flush, and compaction semantics;
- verifier strategy includes independent behavioral checks and anti-shortcut pressure.

Use it to calibrate hard-but-fair hidden-state interactions, realistic partial-state reasoning, and rejection of trivial workarounds.

Do not copy its MVCC/LSM scenario, RocksDB-like concepts, wording, or solution topology.

## How agents should use this registry

Task Architect:
- select 2–4 references that are structurally different from the new task;
- extract only abstract quality signals: number of interacting invariants, realism, partial-state behavior, and verifier depth;
- explicitly check that the proposed task does not resemble their scenario or wording.

Verifier Engineer:
- compare semantic coverage depth and anti-shortcut strategy;
- never port hidden tests or implementation-specific checks from a reference.

Difficulty Reviewer:
- use references to judge whether difficulty comes from reasoning depth rather than ambiguity or sheer task size.

Human Quality Reviewer:
- use references only as calibration for natural engineering tone; never imitate sentences or section pacing.

Compliance Auditor:
- never waive a current Edition 3 rule because a golden reference violates or predates it.
