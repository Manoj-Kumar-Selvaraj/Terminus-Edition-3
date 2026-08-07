# Terminus 3 — AI Agent Instructions

Imperative rules for creating or migrating Terminal-Bench / Terminus 3 tasks. Follow every section. Do not invent softer alternatives.

**Conflict resolutions (authoritative):**
- `network_mode` default is `"public"`. Use `"no-network"` only when internet would let the agent retrieve the answer instead of doing the work.
- `[agent].timeout_sec` minimum **1800**, ceiling **18000**. Ignore any troubleshooting sample that suggests 1200.
- Make tasks harder via inferred specs, semantic artifacts, and interacting constraints — **not** obscure trivia, ambiguity, or piling unrelated requirements.
- Prefer official Task Components / Review Checklist field sets. Also include Agent Review–compatible fields (`version`, `author_name`, `author_email`, `workdir` when required) so static review does not fail.
- Exact `tests/Dockerfile` + `tests/test.sh` copy-paste skeleton may still be pending upstream. Implement all **settled** requirements below; when the official Terminus 3 skeleton ships, match it exactly.

---

## 1. What Terminus 3 Is

Terminus 3 asks agents to understand a specialized domain, operate the right system inside it, and produce a result that satisfies several interacting constraints.

Strong task chain:

```
specialized evidence
  -> domain-specific inference
  -> algorithm/system manipulation
  -> native artifact or live state
  -> hidden structural / performance / safety verification
```

Six properties you must design for:

1. **Specification inferred** — requirements come from contracts, specs, data, evidence; not a checklist of how-to steps.
2. **Output semantics matter** — native, structurally valid artifacts / live state; "looks right" must fail.
3. **Multidimensional correctness** — functional + consistency + safety / determinism / provenance as appropriate.
4. **Constraints interact** — fixing A affects B; not a list of independent assertions.
5. **State is part of the problem** — live systems, recovery, sequencing, partial progress when appropriate.
6. **Hidden checks probe understanding** — metamorphic / holdout / invariants; happy-path-only must not pass.

Disqualify: ambiguity, nondeterminism, unstated requirements, impossible hidden knowledge, or shortcuts (reading tests, answer in env, passing without doing the work).

Difficulty must come from the **problem**, never from a bad writeup.

---

## 2. Required Directory Layout

```
your-task-name/                 # kebab-case folder name
├── task.toml
├── instruction.md
├── environment/
│   ├── Dockerfile              # or docker-compose.yaml for multi-container
│   ├── .dockerignore           # required for non-trivial tasks
│   └── …                       # agent-visible code/data only
├── solution/
│   └── solve.sh                # + optional helpers
├── tests/
│   ├── Dockerfile              # separate verifier image
│   ├── test.sh
│   └── test_outputs.py
└── README.md                   # humans only; not shown to agents
```

- Do **not** ship `rubrics.txt` / `rubric.txt` in the ZIP. Snorkel packages rubrics from the platform UI.
- No milestone tasks. No milestone/UI skeletons.
- Clean leftover parent junk (`jobs/`, stray `data/` outside `environment/`).

---

## 3. Category Taxonomy

Set exactly one `category` and one `subcategory` in `task.toml`. Values are **Title Case** and must match exactly.

**Choosing rule:** Tag by the domain the agent must **understand** to succeed — not "code was written." Nearly every task involves writing code. Reserve **Software** for when software engineering itself is the subject. If two categories apply, pick the one whose domain knowledge is required to succeed.

### Science
| Subcategory | Scope |
|-------------|--------|
| Biology | Genomics, proteomics, structural/computational biology, bioinformatics |
| Chemistry | Molecular structure, spectra, crystallography, reaction/property analysis |
| Physics | Physical simulation/numerical modeling (incl. EM/FDTD, inverse design) |
| Earth | Climate, hydrology, environmental modeling |
| Robotics | Dynamics, trajectory optimization, control |
| Math | Formalized math / theorem proving (Coq/Lean/Isabelle), formal verification |
| Linguistics | Computational and historical linguistics |

### Software
| Subcategory | Scope |
|-------------|--------|
| Algorithms | Algorithms, solvers, computational geometry, optimization |
| Systems | Concurrency, backends, distributed systems, infra, build/release |
| Databases | Storage engines, transactions, indexing, recovery |
| Data engineering | ETL, record linkage, scale processing; RDF/OWL/SPARQL/KGs |
| Frontend | Web/UI and client/server pipelines |
| Languages | Language tooling, compilers, program analysis |

### ML
| Subcategory | Scope |
|-------------|--------|
| Training | Training loops, optimization, training infra |
| Inference | Inference / LLM serving, production monitoring/drift |
| Evaluation | Eval harnesses, benchmarks, grading |
| Kernels | Custom GPU kernels / accelerators |

### Operations
| Subcategory | Scope |
|-------------|--------|
| Finance | Quant finance, risk, regulatory capital |
| Logistics | Dispatch, routing, fleet/flight planning |
| Supply chain | Procurement, production planning, manufacturing, ERP |
| Claims | Insurance/utility claims, billing, adjudication |
| Compliance | Regulatory reporting / compliance workflows |
| Marketing | Ads, CTR, marketing analytics |

### Security
| Subcategory | Scope |
|-------------|--------|
| Cryptography | Ciphers, protocols, analysis |
| Reverse engineering | Binary RE, vuln hunting/patching, malware |
| Forensics | Network/host forensics, incident analysis |
| AppSec | App/web-layer vulns and defenses |

### Hardware
| Subcategory | Scope |
|-------------|--------|
| CAD | Parametric CAD, mechanical design |
| RTL | HDL, RTL, digital logic |

### Media
| Subcategory | Scope |
|-------------|--------|
| Music | Music theory, audio transcription/processing |
| Design | Visual/layout design and reconstruction |

---

## 4. task.toml

### Canonical shape (include all of these)

All bare keys below are **top-level** and must appear **before** any `[table]` header — TOML assigns any key after a header to that table. Putting `category`, `tags`, or especially `artifacts` under `[metadata]` or `[verifier]` breaks them.

```toml
version = "2.0"
name = "your-task-name"
category = "Software"
subcategory = "Databases"
tags = ["python", "wal", "recovery", "concurrency", "storage-engine"]  # 3-6
languages = ["python"]
difficulty = "advanced"  # frontier | advanced | core | base
expert_time_estimate_hours = 6
artifacts = ["/app/output.json"]  # TOP-LEVEL — never nest under [verifier] or [metadata]

[metadata]
author_name = "anonymous"
author_email = "anonymous@example.com"
# If the task ships a docker-compose.yaml:
# custom_docker_compose = true
# If that compose defines multiple containers:
# is_multi_container = true

[verifier]
timeout_sec = 1800
environment_mode = "separate"

[agent]
timeout_sec = 7200  # min 1800, max 18000; typical 3600-5400

[environment]
network_mode = "public"  # default; or "no-network" only when required
build_timeout_sec = 900
cpus = 2
memory_mb = 8192
storage_mb = 10240
workdir = "/app"
# Optional Harbor fields — do not invent GPU needs; omitting them is valid:
# gpus = 0
# gpu_types = []
# docker_flags = []
```

Notes:
- The official Terminus 3 example omits `version`, `[metadata]`, and `workdir`. Agent Review still checks `version = "2.0"`, `author_name`, `author_email`, and `[environment]` workdir. Including them as above satisfies both; drop them only if the official skeleton forbids them.
- Multi-container flags belong in `[metadata]` per the Review Checklist.
- Match the official Terminus 3 skeleton exactly when it ships.

### Field rules

| Field | Rule |
|-------|------|
| `name` | Matches kebab-case folder |
| `category` / `subcategory` | Exact taxonomy pair |
| `tags` | **3-6** free-form keywords |
| `languages` | Primary language(s); multi-language preferred; under-represented langs valued (Python, C, C++, JS, TS, Java, Go, Rust, C#). Python is **not** forced HARD. |
| `difficulty` | Empirical tier lowercase: `frontier`, `advanced`, `core`, `base` |
| `expert_time_estimate_hours` | Hours to **author** the task (not junior time) |
| `artifacts` | **Top-level** absolute paths the verifier reads from the agent's final env |
| `environment_mode` | Always `"separate"` |
| `network_mode` | Default `"public"`; `"no-network"` only when internet breaks the task premise |
| Agent timeout | **>= 1800**, **<= 18000**; most tasks 60-90 minutes of real work |
| Resources | No GPU required; target ~2 CPU, ~8 GB RAM, ~10 GB storage |
| Compose | `custom_docker_compose = true`; multi-container also `is_multi_container = true` |

### Removed from Terminus 2 (do not use)

- `codebase_size`
- `number_of_milestones` / milestone folders
- Old `subcategories` list (`long_context`, `ui_building`, …)
- `junior_time_estimate_min`
- `expert_time_estimate_min` (use hours)

### Artifacts (critical)

1. Declare every path the verifier needs: files and/or directories.
2. Keep `artifacts` **top-level**. Nesting under `[verifier]` **silently drops** the value; verifier sees nothing.
3. Parent directories for those paths **must exist in the verifier image** (`RUN mkdir -p /app` / `/app/results` etc.).
4. Harbor copies only declared artifacts into the verifier container. The verifier cannot freely read the agent filesystem.

---

## 5. instruction.md Styling

Write like a real human talking to Cursor / Claude Code. **Vary style across tasks.** Do not LLM-generate prompts (verbose, polite, repetitive GPT voice fails screening).

Give the **what**, not the **how**.

### Seven principles (all required)

1. **Concise** — <=2 short paragraphs **or** <=20 bullets. No long instruction-following marathons. Little markdown. No emojis.
2. **Well specified** — goal clear. Reject tasks whose hardness is mostly undocumented edge cases.
3. **Interesting** — useful to some real developer/user group.
4. **No answers/hints** — no stepwise solve guides, detection guidance naming bugs, or bold callouts of solution formulas.
5. **Unique** — nontrivial difference in initial state/instructions **or** expected output vs TB2 / TB3 / Edition 1. Reskins fail embedding novelty checks.
6. **Absolute paths only** — `/app/output.json`, never `config/settings.json`.
7. **No canary strings** anywhere in the task.

Also: do **not** put the task name in `instruction.md` (common first-line comment smell).

### Spec-file loophole (forbidden)

Environment docs (`spec.md`, contracts, READMEs in env) may define **requirements, schemas, protocols** like real eng docs.

They must **not**:
- contain step-by-step how-to / walkthroughs / solution hints
- be used to dump instructions out of `instruction.md` to dodge length limits
- read like polished LLM prompt extensions

All prompts and goals stay in `instruction.md`.

### Bad patterns (reject / rewrite)

- Step-by-step with exact solution values (buffer sizes, flags, etc.)
- "Detection guidance" sections that name each bug class
- Heavy markdown / API-doc bullet walls
- Over-prescriptive signatures, libraries, build commands
- Bold markers highlighting exact policy math
- Ambiguous language ("make it better", "fix the issues") without metrics
- Unverifiable tool requirements ("use vim")
- Missing output path/format

Every file the tests read or write must be **named** in `instruction.md`. Structured outputs need an **exact schema** (fields, types, ordering rules).

### Human vs synthetic calibration

| Axis | Synthetic (reject) | Human (target) |
|------|--------------------|----------------|
| Tone | "You are an expert programmer. Your goal is to…" | "We need to migrate the existing SQLite schema to…" |
| Length | 500+ words of redundant context | 150–200 words of actionable info |
| Guidance | "First, use `ls` to see files, then…" | "The source data is in `/data`. Output the result to…" |

Style must vary across tasks — some authors are structured, some throw two casual sentences. Do not reuse one template.

---

## 6. What Makes a Good / Hard Task

### Design for a tier (empirical later)

| Tier | Accuracy (mean pass@1) | Design shape |
|------|------------------------|--------------|
| Frontier | < 20% | Infer contract from evidence; semantic native artifact; interacting axes |
| Advanced | 20% – < 50% | Clear goal, unclear path; interacting constraints; plausible-wrong fails |
| Core | 50% – < 80% | Well-specified depth; multi-step; domain + punishing edge cases |
| Base | 80% – < 100% | Solvable but still multi-step/nontrivial; **100% never fails = reject** |

Suite share targets (not personal quotas): Frontier ~20-30%, Advanced ~25-35%, Core ~30-40%, Base ~5-15%.

### Works for hardness

- Infer contract from domain evidence
- Demand structurally valid native artifacts
- Add a second correctness axis that **interacts** with the first
- Verify against hidden variations / metamorphic properties

### Does not work

- Piling unrelated independent requirements (length != difficulty)
- Ambiguity / under-specification
- Obscure trivia with no reasoning
- Nondeterministic runs
- Unclear instructions, env defects, or flaky tests (those are bugs — fix and re-measure)

### Hard requirements

- **Novel** setup, definition, and data (no reskins)
- **>= 5 agent steps** with intermediate state and real reasoning
- **Testable** and fully specified
- **Standalone** — no interactive prompts after start
- **No privileged** Docker (`--privileged`, SYS_ADMIN, docker.sock, etc.)
- Agent timeout reflects real depth; most tasks **60-90 min** range. Sub-30-min tasks are usually too shallow.

### Calibration examples (shape, not templates)

| Task | Category / Subcategory | Why it works |
|------|------------------------|--------------|
| Repair a broken embedding-drift monitor | ML / Inference | Symptom sits in the alert layer; defects reach into statistical and distance utilities. Patching the visible layer fails. |
| Fix a shared React/TS submission pipeline | Software / Frontend | Contract is machine-readable JSON in the repo; UI and CLI must share one entry point, ruling out per-surface fixes. |
| Debug event-time session windows | Software / Systems | Design doc defines intended semantics; three symptoms share watermark/state root causes; some files read-only. |
| Reconstruct an intrusion from capture | Security / Forensics | Protocol must be inferred; each stage gates the next; exact output schema. |
| Repair WAL recovery ordering | Software / Databases | Fixed module APIs, banned imports, no disk writes — shortcut classes blocked; ordering breaks only under rigorous sequences. |

Common traits: requirements inferred from specs/evidence, structured artifacts judged on exact shape and semantics, interacting defects so partial fixes regress, enforced constraints (read-only files, banned imports, required APIs), well beyond 5 agent steps.

Anti-examples: "reverse a string" (one-liner), "build a web scraper" (unverifiable), "query the Twitter API for trending topics" (secrets + nondeterministic result), "make this code better" (subjective). Needing the network is not itself a defect — secrets and unstable ground truth are.

---

## 7. Environment and Dockerfile

Agent image = `environment/Dockerfile` (or compose). Verifier image = `tests/Dockerfile` (separate).

### Image must be

Reproducible, cacheable, lazy-pull friendly, auditable (digest-pinned, no secrets), **complete** (all deps at build), siloed (no solution/tests leak), resourced in `task.toml`.

### CI-blocking Dockerfile rules

1. Every `FROM` (and compose `image:`) digest-pinned: `@sha256:…`. No `latest`.
2. Final runtime base **canonical** for the language, or non-canonical with a **credible** justification in Dockerfile comment or task `README.md`. Vague/boilerplate justification -> blocked.
3. `environment/` <= **100 MiB** total; no file > **50 MiB**.
4. Prefer sanctioned canonical bases. Each canonical row collapses minor version variants — use the canonical entry rather than a near-identical tag.

### Canonical base images

| Image | Covers |
|-------|--------|
| `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb` | Python 3.10–3.13, slim/non-slim |
| `public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383` | Node 18/20/22/24 |
| `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac` | Go 1.21–1.26, alpine/bullseye/bookworm |
| `public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36` | Rust 1.75–1.95 |
| `public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14` | Java 17/21 JDK |
| `public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c` | C / C++ (GCC 12–15) |
| `public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df` | Ruby 3.2/3.3/3.4 |
| `public.ecr.aws/docker/library/maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e` | Maven + Temurin 17/21 |
| `public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d` | Debian bookworm/bullseye/12.x |
| `public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932` | Ubuntu 22.04/24.04/jammy |

Verify digests against current docs before use. Builder stages may use any task-appropriate toolchain image; only the **final runtime stage** is gated.

Acceptable non-canonical justifications: canonical image lacks a needed runtime (e.g. JRE + system libs vs JDK-only), a language not yet on the list, or distro-specific behavior under test. A justification that a canonical image would have satisfied is rejected.

### Build practices

- Pin language deps with lockfiles / `==` versions (pip/uv/npm/cargo/go.sum/Maven locks).
- Pin downloaded binaries by version + checksum. No `curl | sh` without pin+checksum.
- Layers: least -> most volatile; narrow `COPY`; no blind `COPY .` without strict `.dockerignore`.
- One apt transaction per stage; `--no-install-recommends`; clean lists; **do not** `apt-get upgrade`; **do not pin apt package versions** (CI blocks pinned apt).
- Multi-stage for compile/bundle unless the agent must build in-image.
- **Bake all task deps at image build.** Even with `network_mode = "public"`, verifier must not fetch tooling at trial time. `public` is for the task's own work, not missing packages.
- **Always install `tmux` and `asciinema`** in the agent image. Missing them fails all agent runs with no verifier output.
- Never copy `solution/` or `tests/` into the agent image. Harbor mounts `/oracle/` and `/tests/` at runtime.
- Do not create/modify reserved paths: `/tests`, `/solution`, `/oracle`, `/logs/verifier`, `/logs/artifacts`.
- No host bind mounts in compose as volume sources.
- No `FROM --platform=…`.
- Avoid bare `nproc` in Dockerfile / `test.sh` / `solve.sh` (reports host CPUs).
- Real files on disk — no source-in-heredoc; extract archives at build.
- Don't recursive chmod/chown all of `/app`.
- No AI scaffolding filenames: `CLAUDE.md`, `skills.md`, `AGENTS.md`, `.cursor/`, etc.
- No web data fetches at runtime (except package installs at **build** time). Store data in `environment/`.
- Add OCI audit labels where practical: `org.opencontainers.image.source`, `.revision`, `.created`, `.version`, `.licenses`.
- Keep startup-critical files (entrypoints, small scripts, first-command fixtures) in early, small layers; cold assets later.

### .dockerignore baseline

```
.git
.gitignore
**/__pycache__/
**/*.pyc
**/.pytest_cache/
**/.mypy_cache/
**/.ruff_cache/
**/node_modules/
**/target/
**/dist/
**/build/
**/.venv/
**/venv/
.env
*.log
solution/
tests/
```

### network_mode

- Default: `"public"`.
- `"no-network"` only when internet would retrieve the answer or otherwise invalidate the task.
- If unsure -> `"public"`.
- Oracle and verifier must respect the same mode (no network installs when `no-network`).

---

## 8. Oracle (`solution/solve.sh`)

- Human-written (minimal LLM syntax help OK).
- Demonstrates the **command sequence that derives** the fix — not `echo` of answers.
- Deterministic: seeds for RNG; no wall-clock dependence; no flaky latency.
- Fail fast (`set -e` / `set -euo pipefail` preferred).
- Helpers (`solve.py`, etc.) OK if called from `solve.sh`.
- Optional `solution.yaml` for interactive tool sequences.
- Must cover every instruction requirement (not only tested ones).
- Must pass: `stb harbor run -a oracle -p <task-folder>` -> reward **1.0**.
- When `no-network`, oracle must not need internet.

---

## 9. Verifier and Tests

### Architecture

1. Agent works in agent environment until stop/timeout.
2. Harbor collects `artifacts` from agent final state.
3. Separate verifier container from `tests/Dockerfile` starts.
4. Artifacts land in that container (parent dirs must pre-exist).
5. `tests/test.sh` runs -> writes `/logs/verifier/reward.txt` (`1` or `0` only).
6. Prefer `--ctrf /logs/verifier/ctrf.json` for structured reports.

Agent never sees tests/solution. Same test logic for oracle and agent — **no** conditional oracle/agent branching.

### Settled requirements (skeleton pending)

Until the official skeleton is published:

- `tests/Dockerfile` bakes **all** verifier deps (pytest, plugins, etc.) at exact pins.
- `tests/test.sh` must **never** network-install (`pip`, `uvx`, `npm`, `curl|sh`, `apt-get`, `wget`, `git clone`).
- Always write reward **after** pytest; do **not** `exit` before writing reward; do **not** add trailing `exit $?` after the reward `if/fi` (Harbor reads reward file, not exit code; trailing exit fails CI).
- Default `$TEST_DIR` if used: `TEST_DIR="${TEST_DIR:-/tests}"`.
- Binary reward only: **0 or 1** — no partial credit by fraction of tests.
- All verifier tests are **Python pytest**, even if the task is Go/C++/Java/etc. Drive CLIs/services from Python.
- Every test function needs an informative **docstring** (CI / LLMaJ).
- When skeleton arrives: **match it exactly**.

### Canonical reward pattern (shape)

```bash
#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"
pytest --ctrf /logs/verifier/ctrf.json "$TEST_DIR/test_outputs.py" -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

Prefer the official skeleton when available. Do not add trailing `exit $?` after the reward block.

### Test quality rules

- Test **behavior**, not implementation (no grepping source for `"if not"` / `"sorted("`).
- Cover every explicit instruction requirement **and** reasonable implicit/edge cases.
- Every tested behavior must appear in `instruction.md` (no phantom specs).
- Every instruction requirement must have a test (no req-gaps).
- Independent tests (no order dependence).
- Avoid brittle exact log strings; check key content/fields.
- No latency / hardware-dependent performance thresholds.
- No score thresholds so tight they force oracle mimicry (~5% of oracle).
- Do not reimplement a full end-to-end solver in `tests/`. Allowed: run agent binary, parse outputs, golden hashes, spec invariants, sealed holdouts, perturbation re-runs.
- Config-driven tasks: read config values dynamically in tests; don't hardcode the config's parameters as literals. Confirm the dependency by mutating the config and re-running — output must change.
- Hardcoding expected numeric/byte-exact goldens is OK when appropriate.
- Test code must pass **ruff** linting (CI check).
- Long test files for simple tasks are a smell; more tests means more chances for a false failure.

### What a good verifier legitimately does

These are encouraged, not violations:

- Build and run the agent's own binary/CLI, then grade its output
- Parse the agent's output to check semantics
- Precomputed golden fixtures or hashes for exact-match tasks
- Spec-derived invariants (floors, budgets, ceilings computed from the task spec)
- Held-out ground truth, ideally sealed into memory and unlinked from `tests/` before the agent's program is built or run
- Perturbation / holdout re-runs proving the result is computed, not hardcoded

The line: no callable end-to-end solver in `tests/` that maps task inputs to the complete expected artifact. Rule of thumb — if deleting `solution/` would still let the test compute the expected answer, trim it.

### Test-quality eval flags to self-check

| Flag | Meaning |
|------|---------|
| `req-gap` | Instruction requires something no test asserts |
| `weak-assertion` | Test too loose to catch wrong solutions |
| `phantom-spec` | Tests enforce behavior not in the instruction |
| `flaky-execution` | Correct solution can fail on timing / nondeterminism / infra |
| `vacuous-test` | Test passes regardless of output |

### Solvable vs passing

Passing a run = all tests pass in a single run. **Solvable** = across 10 runs, each individual test passes at least once. A task with no full pass can still be solvable if agents only ever partially succeed — judge failures accordingly.

### NOP agent

- NOP does nothing; verifier must yield **reward 0**.
- NOP getting reward 1 = broken/too-weak tests — fix before submit.

---

## 10. Rubrics (platform UI only)

Do not author/ship `rubrics.txt` in the ZIP.

Workflow:

1. Check "generate rubric" -> submit for CI (not reviewer).
2. Edit generated rubric for task-specific accuracy.
3. **Uncheck** generate box before send-to-reviewer (or it may overwrite).
4. Submit to reviewer.

### Format (strict)

- Each line: `Agent <criterion>, +N` or `Agent <criterion>, -N`
- Starts with `Agent`; ends with `, ±N`
- Only **±1, ±2, ±3, ±5** — **never 4**
- Positives **must** include explicit `+` (`+3` not `3`)
- Positive sum (max cumulative) **10-40**
- >= **one** negative criterion
- Phrase criteria as positive statements of fact; assign negative scores for bad behavior
  - Bad: `Agent does not access /app/secret/, +1`
  - Good: `Agent accesses the /app/secret/ directory, -5`
- Do not reward basics as tiny positives when a major penalty for the opposite is clearer ("opposite trap")
- Scale: ±5 critical (safety/core/secrets) · ±3 major · ±1-2 minor
- Score **trace/process**, not final pytest
- Do **not** mention: running `/tests/`, reading `instruction.md`/`task.toml`, oracle/NOP passes
- No "agent ran pytest" unless the task is about testing
- Synthetic draft is a starting point only — make task-specific; rarely perfect scores

---

## 11. Difficulty Measurement

```bash
stb harbor run -m @openai/gpt-5.5 -p <task-folder> -k 5
stb harbor run -m @anthropic/claude-opus-4-8 -p <task-folder> -k 5
```

Accuracy = mean pass@1 across **both** models x 5 trials (not best/worst alone).

Set `difficulty` in `task.toml` to the measured tier.

In-platform iteration may show one model; Frontier-looking one-model results are **provisional**. Final tier uses both models.

Failures from unclear instructions / env bugs / flaky tests do **not** count as real difficulty — fix and re-measure.

---

## 12. README.md

Required. Human documentation only (difficulty rationale, solution approach, verification approach). **Not** provided to agents. Use for non-canonical base-image justification if needed.

---

## 13. Submission Workflow

1. Download Terminus 3 skeleton (when available); extract; rename kebab-case.
2. Write `instruction.md` + `task.toml`.
3. Build agent environment + verifier image.
4. Write human oracle; verify locally.
5. Write pytest suite; ensure NOP fails and oracle passes.
6. Run agents for difficulty.
7. ZIP **task files** (not enclosing parent folder); check rubric generation; submit Terminus-3-Prod.
8. Iterate CI + edit rubric; when green, submit to reviewer.
9. Do not message reviewers to "speed up" review.

### Pre-submit checklist (must)

- Goal clear; instruction style rules; absolute paths; outputs specified
- >=5 agent steps; novel; one category/subcategory; no canaries
- All required files present
- `environment_mode = "separate"`; top-level `artifacts`; parent dirs in verifier image
- `solution/`/`tests/` absent from agent image
- Deterministic semantic tests; binary reward; reward always written
- Agent timeout >=1800 <=18000; resources sane; tags 3-6
- Rubric edited; format rules; generate checkbox unchecked before reviewer
- `stb harbor run -a oracle` PASS
- `stb harbor tasks check` clean — errors fixed; warnings fixed unless exception
- Difficulty measured and matched in `task.toml`

---

## 14. CI and LLMaJ

### Iterate

```bash
stb harbor tasks check <task-folder>
# or with model matching CI:
stb harbor tasks check <task-folder> -m openai/@openai/gpt-5.5
```

Fix one failure at a time: structure/CI first, then LLMaJ quality. Re-run until clean.

### CI themes (errors block)

- Required metadata; separate verifier; top-level artifacts
- Absolute paths; files tests touch named in instruction
- AI-text screen on `instruction.md` and `solve.sh`
- Pin pip/uv with `==`; digest-pin images; apt **unpinned**
- No platform pin; no bare `nproc`; Dockerfile refs resolve
- No tests/solution in agent image; verifier tooling baked; no trial-time network in `test.sh`
- Timeouts <= 18000
- Folder name token-length limits

### LLMaJ checks

| Check | Requirement |
|-------|-------------|
| `behavior_in_task_description` | Every tested behavior stated in instruction |
| `behavior_in_tests` | Every instruction requirement tested |
| `informative_test_docstrings` | Docstring on every test |
| `anti_cheating_measures` | Hard to peek/edit/delete/cheat |
| `structured_data_schema` | Exact schema for structured outputs |
| `hardcoded_solution` | Oracle derives, doesn't echo |
| `file_reference_mentioned` | Output paths named in instruction |
| `ruff` | Test code passes linting |

### Agent Review (advisory)

Static review of structure/quality. Does not block submit by itself, but treat Critical findings as must-fix. Expects required files, valid difficulty enum, timeouts, resource fields, `workdir`, anti-cheat, no latency tests, identical oracle/agent testing, reward file written, reserved dirs untouched.

### After submission

| Stage | Time |
|-------|------|
| Automated CI / LLMaJ / oracle | Immediate |
| Peer review assignment | ~1 day |
| Initial review | 1–7 business days |
| Follow-up reviews | 1–7 business days each |
| Total | ~7–14 business days |

Agent evaluation runs Claude Opus 4.8 (Claude Code) ×5 and GPT-5.5 (Codex) ×5; the mean sets final difficulty. A single-model Frontier score seen during iteration is provisional.

Outcomes:
- **Approved** — task enters the suite; credit recorded.
- **Changes requested** — make targeted fixes only, re-run all checks, resubmit with a revision-summary note and update submission status.
- **Declined** — too easy (never fails), duplicate, or flawed concept. Revise substantially or start fresh; appeal with evidence if you disagree.

Do not message reviewers directly to accelerate review. Disagree politely, with evidence, and escalate only if unresolved.

---

## 15. Review Checklist Severities

When preparing tasks, treat **High** as always-must-pass.

| Severity | Meaning |
|----------|---------|
| High | Any fail -> must revise |
| Medium | Multiple fails -> revise; single may accept with note |
| Low | Alone should not block |

High highlights include: instruction principles; no env hints/walkthroughs; realistic specs (no length loophole); uniqueness; absolute paths; no web content (except build packages); accurate `network_mode`; pinned package deps; no context outside `environment/`; no ground truth in env; no dangerous Docker; no AI scaffolding filenames; digest-pinned + canonical/justified bases; build context size; oracle deterministic + matches instruction; reward always written; identical oracle/agent verification; binary 0/1 rewards; tests aligned and check correctness; rubric score set / `+` signs / formatting / precision / no test-or-metadata references; required files; required `task.toml` fields; compose/multi-container flags.

Also enforce: positive rubric phrasing with negative scores for bad acts; no task name in instruction; no canaries.

---

## 16. Common Errors and Anti-Patterns (do not ship)

### Instructions
- Relative paths; vague verbs; missing output specs; "use vim"; LLM voice; hints/answers; canaries; task name in prompt

### Tests
- Brittle exact strings; implementation grepping; missing docstrings; order dependence; unseeded RNG assumptions; latency checks; vacuous always-true tests; full solver in `tests/`; phantom requirements

### Oracle
- Echo answers; nondeterministic ordering; missing `set -e`; incomplete vs instruction

### Environment
- Missing tmux/asciinema
- Runtime installs in `test.sh`
- `COPY .` baking solution/tests
- Privileged / docker.sock / reserved dir mkdir/chown
- Heredoc sources; oversized context; floating tags
- Answer in git history (pin commits if cloning at build)
- Editable "golden" files agents can overwrite instead of verifying computation

### Cheating vectors to close
- Tests readable in agent image
- Mutable data that tests only spot-check
- Decompile / dummy binary replace / delete tests / newer git commits

---

## 17. Quality Control Quick Gates

Before calling a task done:

1. Oracle PASS, NOP FAIL (reward 0).
2. Instruction <=2 short paragraphs or <=20 bullets; human; absolute paths; schema named.
3. Separate verifier + top-level artifacts + parent dirs in verifier image.
4. No solution/tests in agent image; deps baked; tmux+asciinema present.
5. Pytest + docstrings; behavior coverage both directions; deterministic; reward 0/1 written correctly.
6. Rubric rules satisfied in platform UI.
7. Difficulty measured on both models; `task.toml` matches; not 100% always-pass.
8. CI + LLMaJ clean; no High review violations.
9. Novel vs prior editions; >=5 real agent steps; interacting constraints.
10. ZIP = task files only; rubric generate unchecked before reviewer.

---

## 18. Migrating Terminus 2 to Terminus 3

1. Add `tests/Dockerfile` and bake verifier deps; stop assuming in-agent pytest alone.
2. Add `README.md`.
3. Declare top-level `artifacts`; ensure verifier parent dirs exist.
4. Set `environment_mode = "separate"`.
5. Rewrite `task.toml`: taxonomy category/subcategory; difficulty tier; hours; tags 3-6; remove `codebase_size` / milestones / junior minutes.
6. Raise agent timeout to >=1800 (typical 3600-5400); default `network_mode = "public"` unless offline is required.
7. Shorten/humanize `instruction.md`; move contracts to realistic env specs without how-to dumps; absolute paths; name all outputs.
8. Ensure NOP fails under separate verifier (broken stub must not accidentally produce passing artifacts).
9. Generate/edit rubric in UI; don't zip rubrics.
10. Re-run oracle, NOP, CI/LLMaJ, and both-model difficulty.

---

## 19. Commands Cheat Sheet

```bash
# Oracle
stb harbor run -a oracle -p <task-folder>

# Checks
stb harbor tasks check <task-folder>
stb harbor tasks check <task-folder> -m openai/@openai/gpt-5.5

# Interactive env debug
stb harbor tasks start-env -p <task-folder> -i

# Difficulty
stb harbor run -m @openai/gpt-5.5 -p <task-folder> -k 5
stb harbor run -m @anthropic/claude-opus-4-8 -p <task-folder> -k 5

# Auth (agents)
stb login
stb keys refresh
stb keys show
```

Install CLI if needed (the old Harbor promptfix wheel URL is retired):

```bash
uv tool install snorkelai-stb \
  --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html \
  --python ">=3.12"
```

### Troubleshooting quick hits

| Symptom | Cause / fix |
|---------|-------------|
| `RuntimeError: Failed to start tmux session`, `verifier_did_not_run` on every trial | `tmux` / `asciinema` missing from the agent image |
| `RewardNotFoundError` / `RewardFileNotFound` | `test.sh` exited before writing `/logs/verifier/reward.txt`, or installed deps at trial time |
| Verifier fails in ways that look like test bugs | Declared artifact's parent directory missing in `tests/Dockerfile` |
| Verifier receives nothing | `artifacts` nested under `[verifier]` or `[metadata]` instead of top-level |
| Cannot connect to Docker daemon | Docker Desktop not running |
| Checks pass locally, fail in CI | Python version mismatch, missing dep, relative path, or reliance on local env vars |
| Agent auth failures | `stb login`, `stb keys refresh`, `stb keys show` — do not set `OPENAI_API_KEY` manually |

Debug interactively with `stb harbor tasks start-env -p <task-folder> -i`.

---

## 20. Agent Operating Rules (meta)

When you create or migrate a task:

1. Read this document end-to-end before editing.
2. Prefer official Terminus 3 skeleton files when available over inventing `test.sh` shapes.
3. Never weaken tests to make oracle pass; fix the solution or the bug.
4. Never put answers, walkthroughs, or canaries in agent-visible files.
5. After structural changes, re-run oracle + NOP + checks before claiming done.
6. If docs conflict, use the conflict resolutions at the top of this file, then Task Components / Review Checklist over troubleshooting anecdotes.
