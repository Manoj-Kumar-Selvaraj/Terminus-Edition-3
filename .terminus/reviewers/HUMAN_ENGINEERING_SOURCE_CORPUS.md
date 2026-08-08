# Human Engineering Source Corpus

Corpus version: `1.0`

Purpose: calibrate the Terminus Instruction Writer and Instruction Reviewer against real public engineering communication. This is not a copy bank and not a style template. Agents must learn structural signals from the sources and must not reproduce source wording.

The sources below are public issue reports written by engineers/users in real projects. The corpus stores only short metadata and generalized observations; it does not copy long issue bodies.

## How to use this corpus

Before drafting a new instruction, the Instruction Writer must sample at least 8 entries spanning at least 4 ecosystems and identify:

- how the reporter opens the issue;
- how much context is actually included;
- whether expected/observed behavior is explicit or implicit;
- how reproduction details are separated from the request;
- what the reporter leaves to existing system knowledge/docs;
- any rough, uneven, or domain-specific wording that demonstrates non-synthetic information selection.

The writer then drafts from the task's own incident. It must not imitate sentences from the sources.

The Instruction Reviewer samples a different set of at least 6 entries before making a final human-signal judgment.

## Source observations

### HC-001 — Go runtime/build cache issue
Source: https://github.com/golang/go/issues/69179
Project: Go
Shape: production symptom + operational context
Observation: The report opens with the concrete build failure, then explains when it disappears and why reproduction is difficult. It does not inventory every compiler invariant. Context is included because it changes diagnosis, not because a template demands completeness.
Signals: incident-first, selective context, imperfect reproducibility, causal suspicion separated from fact.

### HC-002 — Go typed-nil issue
Source: https://github.com/golang/go/issues/53768
Project: Go
Shape: minimal behavior discrepancy
Observation: The author describes one operation, one expected result and one observed result. The prose is direct and slightly rough. It does not explain the entire interface/type system.
Signals: narrow scope, concrete expectation, no benchmark preamble.

### HC-003 — Go formatter second-pass issue
Source: https://github.com/golang/go/issues/62559
Project: Go
Shape: odd real-world reproducer
Observation: The reporter admits they could not produce a clean minimal example and supplies the awkward artifact they actually had. Real reports often contain this asymmetry rather than a perfectly curated specimen.
Signals: candid limitation, evidence over polish, non-symmetric narrative.

### HC-004 — systemd mount regression
Source: https://github.com/systemd/systemd/issues/30395
Project: systemd
Shape: regression report
Observation: Version/distribution context is structured by the project template, while the core ask remains extremely simple: the system should initialize instead of waiting on a missing disk indefinitely.
Signals: one operational failure, environment facts separated from desired outcome.

### HC-005 — systemd bad-unit diagnostic
Source: https://github.com/systemd/systemd/issues/37810
Project: systemd
Shape: observability/diagnostic request
Observation: The writer shows the unhelpful message and states the practical information they wanted. They do not prescribe how systemd should implement the diagnostic.
Signals: output-driven, outcome not implementation, concrete command evidence.

### HC-006 — systemd suspend regression
Source: https://github.com/systemd/systemd/issues/33626
Project: systemd
Shape: intermittent operational failure
Observation: The title already carries much of the incident. The body provides frequency and a representative log. It does not turn intermittent behavior into a long list of edge cases.
Signals: frequency as useful context, evidence-first, economical ask.

### HC-007 — Terraform 1.6 crash
Source: https://github.com/hashicorp/terraform/issues/33977
Project: Terraform
Shape: upgrade regression
Observation: The expected behavior is one sentence. The strongest context is that the same release process worked hours earlier. Real engineers commonly use temporal comparison as evidence without over-explaining the architecture.
Signals: before/after evidence, terse expectation, operational timeline.

### HC-008 — Terraform invalid-workspace automation hang
Source: https://github.com/hashicorp/terraform/issues/21393
Project: Terraform
Shape: automation semantics bug
Observation: The author starts from the practical consequence (automation blocks), quotes the relevant interface promise, then shows actual CLI behavior. The request is defined by user-visible semantics, not an implementation plan.
Signals: consequence-first, contract reference, exact reproduction, no solution hint.

### HC-009 — Kubernetes immutable-field error
Source: https://github.com/kubernetes/kubernetes/issues/118645
Project: Kubernetes
Shape: UX/diagnostic defect
Observation: The report begins with a surprising real operation: applying the same content twice can fail. The huge error dump is evidence; the prose itself stays short.
Signals: concise narrative + raw evidence, one surprising invariant.

### HC-010 — Docker Compose SSH context run failure
Source: https://github.com/docker/compose/issues/7724
Project: Docker Compose
Shape: behavior matrix
Observation: The writer lists one failing command and three nearby commands that work. This is a strong human diagnostic pattern: contrast the smallest meaningful set instead of describing every feature.
Signals: comparative reproduction, local contrast, concrete expected result.

### HC-011 — Docker Compose profile/down issue
Source: https://github.com/docker/compose/issues/8139
Project: Docker Compose
Shape: feature interaction bug
Observation: Three reproduction steps, one observed result, one expected result. The writer adds a short appreciative aside that is irrelevant to the technical contract; real communication often contains such unevenness.
Signals: very small reproduction, explicit contrast, human side-comment.

### HC-012 — Docker tmpfs stack difference
Source: https://github.com/docker/compose/issues/7456
Project: Docker Compose
Shape: equivalent-path inconsistency
Observation: The report compares two ways of creating nominally equivalent containers and shows the resulting filesystem sizes. The core requirement is equivalence, not a list of internal mount rules.
Signals: A/B comparison, observable state, evidence-heavy prose.

### HC-013 — Grafana Loki parse failure
Source: https://github.com/grafana/grafana/issues/92371
Project: Grafana
Shape: simple user-facing bug
Observation: The body is extremely short: what failed and what should have happened. It demonstrates that real prompts can be sparse when the symptom is self-explanatory.
Signals: brevity, no justification paragraph, direct expectation.

### HC-014 — Grafana internal Git Sync
Source: https://github.com/grafana/grafana/issues/105216
Project: Grafana
Shape: new-feature limitation
Observation: The writer explains that the feature works with public GitHub but not an internal Git host and notes there is no previous behavior because the feature is new. This is ordinary, contextual writing rather than polished specification prose.
Signals: contrast, explicit uncertainty/history, natural repetition.

### HC-015 — Grafana package install failure
Source: https://github.com/grafana/grafana/issues/127164
Project: Grafana
Shape: packaging regression
Observation: The report opens with the failed command and its output. The title carries the key precondition (pre-existing data directory). The body does not restate every package-install expectation.
Signals: title/body information split, command evidence, selective precondition.

### HC-016 — Grafana nested notification routing
Source: https://github.com/grafana/grafana/issues/75307
Project: Grafana
Shape: configuration interaction
Observation: The author gives only the routing hierarchy required to reproduce the unexpected receiver choice. The reproduction is sequential because the system is state/configuration dependent, not because the author is giving implementation steps.
Signals: topology-specific reproduction, expected ownership, no solver hints.

### HC-017 — Node npm install regression
Source: https://github.com/nodejs/node/issues/62425
Project: Node.js
Shape: release regression
Observation: The author gives three shell steps, says it reproduces always, and expects installation success. This is a common operational ticket shape: reproducibility + concrete command + failure, with little explanatory prose.
Signals: compact steps, frequency, direct expected outcome.

### HC-018 — Node inspector crash
Source: https://github.com/nodejs/node/issues/57606
Project: Node.js
Shape: subsystem crash
Observation: Conditions are described broadly because the crash has several triggers. The report does not pretend a single exact hidden case is the whole problem.
Signals: condition family, honest scope, crash evidence.

### HC-019 — Prometheus latest-tag regression
Source: https://github.com/prometheus/prometheus/issues/18962
Project: Prometheus
Shape: release/distribution regression
Observation: The report references a previous issue, states the regression in one sentence, and gives the version mismatch. It relies on shared project context instead of re-explaining Docker tag semantics.
Signals: prior-history reference, concise regression, shared-context assumption.

### HC-020 — Alertmanager config reload race
Source: https://github.com/prometheus/alertmanager/issues/3407
Project: Alertmanager
Shape: stateful/race incident
Observation: The writer gives an operational sequence because timing/state matters, then explains the harmful notification sequence in plain terms. The request is about preserved notification semantics, not the locking implementation.
Signals: stateful reproduction, concrete consequence, implementation-neutral.

### HC-021 — Alertmanager 429 handling
Source: https://github.com/prometheus/alertmanager/issues/2121
Project: Alertmanager
Shape: protocol behavior bug
Observation: The author describes how they instrumented a webhook, the HTTP status involved, expected retry semantics and actual behavior. The protocol itself supplies most of the contract.
Signals: protocol reference, one expected semantic, compact context.

### HC-022 — Alertmanager config validation gap
Source: https://github.com/prometheus/alertmanager/issues/1827
Project: Alertmanager
Shape: validator false-success
Observation: One command and its expected/actual terminal output define the issue. The ticket is highly testable without becoming a rubric.
Signals: executable example, exact visible behavior, minimal narration.

### HC-023 — Alertmanager output-format flag
Source: https://github.com/prometheus/alertmanager/issues/3741
Project: Alertmanager
Shape: CLI contract violation
Observation: The report uses the existing `--output=json` flag as the contract and contrasts expected JSON with actual comma-separated output. Existing interfaces are referenced instead of restated as prose.
Signals: interface-as-contract, concrete A/B output, concise ask.

### HC-024 — etcd restore leaves cluster unusable
Source: https://github.com/etcd-io/etcd/issues/14190
Project: etcd
Shape: recovery workflow failure
Observation: The author describes the restore procedure and then the inability to create/delete Kubernetes resources. The procedure is evidence for reproducing state; it is not a proposed fix.
Signals: workflow reproduction, downstream symptom, state transition context.

### HC-025 — etcd slow watcher latency
Source: https://github.com/etcd-io/etcd/issues/18109
Project: etcd
Shape: performance diagnosis
Observation: The author supplies traces and then lists several possible avenues explicitly as exploration, not as requirements. Human reports often separate hypotheses from the requested behavior.
Signals: evidence/hypothesis distinction, quantified symptom, exploratory alternatives.

### HC-026 — etcd election observation
Source: https://github.com/etcd-io/etcd/issues/18163
Project: etcd
Shape: code-path reasoning report
Observation: The author reasons from existing source behavior and admits where guarantees are uncertain. This is useful calibration for technical prose that is sophisticated but not artificially certain.
Signals: uncertainty language, source-backed reasoning, limited claim scope.

### HC-027 — CoreDNS empty resolv.conf crash
Source: https://github.com/coredns/coredns/issues/5764
Project: CoreDNS
Shape: environment edge condition
Observation: The report states the actual deployment condition, desired behavior and minimal reproduction. It includes rough grammar and duplicated references but remains easy to understand.
Signals: real operator voice, minimal environment condition, no polished taxonomy.

### HC-028 — CoreDNS version regression on EKS
Source: https://github.com/coredns/coredns/issues/5159
Project: CoreDNS
Shape: upgrade bisect evidence
Observation: The strongest argument is the immediate behavior change between adjacent CoreDNS versions while the cluster stays the same. The writer uses version comparison rather than constructing a complete DNS specification.
Signals: version isolation, operator observation, diagnostic comparison.

### HC-029 — systemd library build regression
Source: https://github.com/systemd/systemd/issues/33302
Project: systemd
Shape: dependency interaction
Observation: The issue states the enabling option and dependency version that trigger the failure, then supplies the build log. The expected state is simply a successful build.
Signals: triggering condition, raw evidence, sparse desired outcome.

### HC-030 — Go rare stack corruption
Source: https://github.com/golang/go/issues/64781
Project: Go
Shape: rare production failure
Observation: The reporter openly explains that the issue was held back because there was no smoking gun and that affected customer access is limited. This is highly human uncertainty and provenance reporting.
Signals: incomplete evidence acknowledged, customer context, non-artificial confidence.

## Derived writing rules

The corpus supports these recurring patterns:

1. **Incident before taxonomy.** Real reports usually start with the failure/change, not a complete contract summary.
2. **Evidence can be long while prose stays short.** Logs/config/reproduction carry detail that does not belong in a polished paragraph.
3. **Shared context is assumed.** Existing flags, schemas, runbooks and interfaces are referenced rather than redefined.
4. **Expected behavior is often one sentence.** The complexity belongs in the system state, not in verbose acceptance prose.
5. **Human reports preserve uncertainty.** They say when reproduction is hard, a cause is suspected, or a condition is unknown.
6. **Useful asymmetry is normal.** Some sections are detailed because evidence exists; others are one line or absent.
7. **Comparisons are common.** Works-before/fails-now, command A/command B, version X/version Y are strong diagnostic forms.
8. **Implementation proposals are separated from requirements.** When authors suggest fixes, they are hypotheses, not mandatory solution instructions.
9. **Real writers omit obvious justification.** They rarely explain why a crash, duplicate payment or blocked automation is undesirable.
10. **Natural roughness is not a goal.** Spelling mistakes or informal phrasing may occur, but the agent must never fabricate errors as a humanization technique.

## Anti-imitation rule

The Instruction Writer must not copy openings, sentence shapes, issue-template headings or distinctive wording from any source above. The corpus teaches **selection and structure**, not phrasing.

A draft that looks like a GitHub issue template filled mechanically is still synthetic.
