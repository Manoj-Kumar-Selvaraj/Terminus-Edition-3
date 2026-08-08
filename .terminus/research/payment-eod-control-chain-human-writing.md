# Payment EOD human-writing calibration

POLICY_VERSION: HUMAN_WRITING_RESEARCHER 1.0
TASK: payment-eod-control-chain
RESEARCH_DATE: 2026-08-08
STATUS: CALIBRATION_READY
SOURCES_REVIEWED: 24
ECOSYSTEMS: Spring Batch, Temporal, Stripe, Go, systemd, Terraform, Docker Compose, Alertmanager, etcd, CoreDNS
SOURCE_DIVERSITY: PASS — no repository exceeds 25% of the sample

## Task-specific writing profile

### COMMON_OPENINGS

Real reports in this sample usually open with one of these:

- the exact thing that went wrong after a restart/retry/upgrade;
- a concrete contrast such as “first run works, retry repeats X”;
- the operator consequence (blocked workflow, duplicate side effect, stale output);
- a short “we are seeing…” statement followed by the smallest useful state context.

They rarely open with a complete taxonomy of the system or a polished summary of all acceptance invariants.

### COMMON_CONTEXT_FIELDS

For stateful restart incidents, engineers tend to include only context that changes the diagnosis:

- what durable work already completed;
- what was retried/restarted;
- whether the second invocation used the same identity/parameters;
- the visible duplicate/inconsistent effect;
- relevant version or execution-state comparison;
- where the authoritative state is expected to live.

The source population does not normally restate all downstream accounting/business rules in the incident body when those rules already exist elsewhere.

### COMMON_EVIDENCE_FORMS

- one or two shell commands;
- short before/after parameter comparisons;
- logs showing the reused/repeated state;
- a small sequence of operations (complete A, fail B, retry workflow);
- a referenced existing interface or documented behavior;
- a statement that the previous version/path worked.

Evidence is often much more detailed than the prose around it.

### WHAT_REAL_REPORTERS_LEAVE_IMPLICIT

- why duplicate financial effects are undesirable;
- basic meaning of restart/idempotency in the project;
- implementation choices such as which constraint, transaction or helper must be used;
- obvious details already defined by existing record/layout/protocol documentation;
- every edge case implied by the same operational invariant.

### EXPECTED_VS_OBSERVED_PATTERNS

The strongest pattern for this task is contrast:

- a completed side effect exists -> retry should resume it, but it executes again;
- a new identity/parameter set should create new work, but old failed state is reused;
- a held/failed run should not look successful, but stale success artifacts remain;
- a retry should preserve completed side effects, not recreate them.

Expected behavior is normally one short outcome statement. The failure narrative carries the rest.

### UNCERTAINTY_PATTERNS

Several real reports openly distinguish fact from hypothesis:

- “I may be misunderstanding the retry model”;
- “we have not found a way to clear this state”;
- “this appears to happen after…”;
- “the same flow worked before the upgrade.”

For this benchmark task the incident itself is known, so we should not invent uncertainty. But we should also avoid artificial certainty about implementation details that the operator would not know.

### IMPLEMENTATION_HINT_RISK

Restart/idempotency reports easily become prescriptive when authors propose locks, replay APIs, retry policies, unique keys or workflow flags. Those proposals are useful context in public issues but must not become solution requirements in `instruction.md` unless the actual task contract requires that mechanism.

For this task the instruction should describe safe restart semantics and authoritative durable state, not tell the solver which SQL constraint, transaction shape or shell function to use.

### PROJECT_TEMPLATE_BIAS

Temporal and some other repositories use issue-form headings such as “Expected Behavior”, “Actual Behavior”, “Steps to Reproduce”, or feature-request prompts. These headings are repository templates, not evidence that natural engineer prompts should always use that structure.

The Spring Batch legacy issue is closer to an organic incident narrative: setup, what happened, comparison with the previous release, and the practical consequence.

### DO_NOT_IMITATE

- GitHub issue-template headings;
- exhaustive numbered behavior matrices from long issue discussions;
- exact public wording such as “skip completed activities on retry”;
- implementation proposals from Temporal/Spring Batch maintainers;
- copied sentence rhythm or distinctive phrases;
- artificial typos/slang added to appear human.

## Source notes

### HWP-001 — Spring Batch restart uses wrong job parameters
Source: https://github.com/spring-projects/spring-batch/issues/882
Type: batch restart regression
Structural observation: The reporter explains a small failed-job sequence, then contrasts the parameters supplied for the next launch with the parameters actually reused. The real complaint is obvious before any solution proposal appears. Later comments expand edge cases, but the original incident remains concrete.

### HWP-002 — Temporal workflow retry repeats completed external side effect
Source: https://github.com/temporalio/temporal/issues/8901
Type: retry/idempotency feature request
Structural observation: Starts from a real sequence: one activity creates durable external state, a later activity fails, workflow retry recreates the first side effect. The author explains why deleting the first side effect is unsafe. This is very close to the information-selection pattern needed for EOD restart writing.

### HWP-003 — Temporal WorkflowTaskTimeout retry-policy confusion
Source: https://github.com/temporalio/temporal/issues/1848
Type: retry behavior bug report
Structural observation: Very small expected/actual contrast plus a two-step reproducer. The maintainer discussion later clarifies semantics; the reporter did not try to encode the entire workflow model in the opening prompt.

### HWP-004 — Temporal corrupted history after oversized arguments
Source: https://github.com/temporalio/temporal/issues/1267
Type: durable-state corruption
Structural observation: Expected result is one sentence. Actual result describes the corrupt durable state and downstream inability to inspect/clear it. Strong example of describing the state consequence rather than prescribing internal repair.

### HWP-005 — Temporal list results intermittently inconsistent
Source: https://github.com/temporalio/temporal/issues/5364
Type: state/visibility inconsistency
Structural observation: Repeated command output is used as evidence. Narrative prose is short. The command carries the technical detail.

### HWP-006 — Temporal retry routing request
Source: https://github.com/temporalio/temporal/issues/4600
Type: retry policy interaction
Structural observation: Uses concrete error classes and operational consequences to explain why one retry policy is insufficient. The author separates desired behavior from possible implementation details.

### HWP-007 — Temporal continue-as-new signal carryover
Source: https://github.com/temporalio/temporal/issues/8097
Type: state transition feature request
Structural observation: Opens with the current behavior and why it is reasonable in one close path but wrong in another. The requested semantic change is compact.

### HWP-008 — Temporal child workflow conflict behavior
Source: https://github.com/temporalio/temporal/issues/6799
Type: identity/conflict semantics
Structural observation: Discussion is about what should happen when the same identity already exists. Useful calibration for identity/replay language: the key concept is behavior under an existing durable identity, not a long implementation specification.

### HWP-009 — Stripe Go retry documentation
Source: https://github.com/stripe/stripe-go
Type: API retry/idempotency engineering documentation
Structural observation: Retry safety is explained by connecting automatic retries to idempotency keys. The documentation names the invariant but does not enumerate every duplicate-side-effect scenario.

### HWP-010 — Go build/cache operational failure
Source: https://github.com/golang/go/issues/69179
Type: production build failure
Structural observation: Opens with the concrete failure and conditions under which it disappears. Includes uncertainty about reproducibility rather than inventing a perfectly minimal benchmark-like narrative.

### HWP-011 — Go typed-nil behavior discrepancy
Source: https://github.com/golang/go/issues/53768
Type: narrow behavior bug
Structural observation: One operation, expected behavior, actual behavior. No explanatory essay around the language model.

### HWP-012 — Go formatter second-pass issue
Source: https://github.com/golang/go/issues/62559
Type: reproducer-quality limitation
Structural observation: Author candidly says a clean minimal reproducer was difficult and shares the available artifact. Real engineering evidence can be uneven.

### HWP-013 — systemd mount regression
Source: https://github.com/systemd/systemd/issues/30395
Type: boot/operational regression
Structural observation: The core ask is simple and user-visible. Environment/version details are separate from the desired outcome.

### HWP-014 — systemd bad-unit diagnostic
Source: https://github.com/systemd/systemd/issues/37810
Type: diagnostics request
Structural observation: Shows the unhelpful result and states the information the operator needed. Does not prescribe the code path to implement it.

### HWP-015 — Terraform upgrade crash
Source: https://github.com/hashicorp/terraform/issues/33977
Type: upgrade regression
Structural observation: The strongest evidence is temporal: same process worked shortly before, then failed after upgrade. Expected behavior remains terse.

### HWP-016 — Terraform invalid-workspace automation hang
Source: https://github.com/hashicorp/terraform/issues/21393
Type: automation semantics
Structural observation: Starts with the practical consequence, references the existing interface promise, and demonstrates actual CLI behavior. Good model for pointing to existing contracts rather than reproducing them.

### HWP-017 — Docker Compose SSH-context failure
Source: https://github.com/docker/compose/issues/7724
Type: command-path inconsistency
Structural observation: One failing command contrasted with nearby commands that work. Small comparison set gives diagnosis without a long prose taxonomy.

### HWP-018 — Docker Compose profile/down issue
Source: https://github.com/docker/compose/issues/8139
Type: feature interaction
Structural observation: Three short reproduction steps plus expected/actual. Natural side-comment appears, but that roughness is not something to fabricate.

### HWP-019 — Alertmanager config-reload race
Source: https://github.com/prometheus/alertmanager/issues/3407
Type: stateful/race incident
Structural observation: Describes the operational sequence because state/timing matters, then states the harmful notification result. It does not tell maintainers which lock/state machine to implement.

### HWP-020 — Alertmanager HTTP 429 handling
Source: https://github.com/prometheus/alertmanager/issues/2121
Type: retry/protocol semantics
Structural observation: Existing protocol semantics provide the contract, so the reporter needs only the status, expected retry behavior and observed behavior.

### HWP-021 — etcd restore leaves system unusable
Source: https://github.com/etcd-io/etcd/issues/14190
Type: recovery workflow
Structural observation: Restore procedure is evidence for reproducing durable state; the request itself is not a recovery algorithm walkthrough.

### HWP-022 — etcd slow watcher latency
Source: https://github.com/etcd-io/etcd/issues/18109
Type: performance diagnosis
Structural observation: Detailed traces coexist with a relatively short narrative. Hypotheses are explicitly separated from requirements.

### HWP-023 — CoreDNS version regression on EKS
Source: https://github.com/coredns/coredns/issues/5159
Type: version/regression isolation
Structural observation: Adjacent-version comparison is the main diagnostic argument. The author does not restate DNS behavior comprehensively.

### HWP-024 — CoreDNS empty resolv.conf crash
Source: https://github.com/coredns/coredns/issues/5764
Type: environment edge condition
Structural observation: Actual deployment condition, desired behavior and minimal reproduction are enough. Rough grammar does not prevent clear intent, but we should not deliberately reproduce roughness.

## Writer warnings for this task

1. Do not list the 29 defect manifestations or the 28 F2P cases in prose.
2. Do not describe the database constraints, triggers or ledger-repair mechanism.
3. Do not re-summarize every record field from the solver-visible docs.
4. Prefer the observed restart failures: repeat financial work + stale success-looking output.
5. State that the database is restart authority because that is a non-obvious operational constraint.
6. Refer to the three existing `/app/eod/docs/...` files for identity/interface/finance-close details.
7. Keep “fresh / partial / completed” only if it helps describe the expected restart envelope; do not turn it into three mini acceptance lists.
8. Keep success authorization clearly later than reconciliation because otherwise the incident is under-specified.
9. Avoid polished phrases like “the cycle must still satisfy the finance controls” if a simpler operator phrase works.
10. Do not mention hidden test counts, defect counts, large-system profile or benchmark terminology.

## Reviewer warnings

A draft should be revised if it sounds like an abstract payment-system specification rather than somebody handing off a restart bug. A technically complete paragraph can still be synthetic if every clause looks intentionally paired with a verifier family.
