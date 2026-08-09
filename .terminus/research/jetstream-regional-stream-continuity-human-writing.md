# Human-writing research — jetstream-regional-stream-continuity

Writer calibration sampled eight corpus entries across eight practical ecosystems before freezing the instruction. The observations below are selection notes only; no source wording is reused.

| Corpus entry | Ecosystem | Opening move | Evidence placement | Omitted/shared context | Expected vs observed | Calibration takeaway |
|---|---|---|---|---|---|---|
| HC-001 | Go | concrete production/build symptom | awkward reproduction follows symptom | compiler internals left to project knowledge | disappearance under changed condition is evidence | start from the reconnect/archive symptom, not JetStream taxonomy |
| HC-006 | systemd | intermittent operational failure | representative log carries most detail | no exhaustive edge-case inventory | frequency/log contrast implies desired reliability | let archived controller log carry detailed reconnect evidence |
| HC-008 | Terraform | practical automation consequence | exact interface/reproduction after consequence | shared CLI contract is referenced | promised semantics contrasted with blocking behavior | point to continuity contract rather than restating every invariant |
| HC-010 | Docker Compose | one failing operation | nearby working operations form compact comparison | no architecture essay | one path fails while adjacent paths work | use edge-journal vs hub-archive disagreement as the diagnostic contrast |
| HC-020 | Alertmanager | stateful operational sequence | event sequence is evidence, not a fix recipe | locking/implementation left unspecified | harmful outcome described plainly | mention reconnect + duplicate effect + halted replay, not the internal repair order |
| HC-024 | etcd | recovery workflow then downstream symptom | restore procedure explains inherited state | storage internals assumed | cluster appears restored but downstream state is wrong | transport/cluster health can be green while application continuity remains wrong |
| HC-028 | CoreDNS | version/condition contrast | adjacent behavior supplies causal evidence | DNS implementation left to maintainers | same environment, different runtime behavior | keep task evidence focused on what changed around reconnect |
| HC-019 | Prometheus | terse regression statement | version/history reference does most context work | container/tag semantics assumed | previous behavior provides expectation | avoid explaining obvious distributed-streaming background in instruction |

## Task-specific information-selection profile

Opening: the west edge has reconnected, but the central archive still does not reconcile with the edge journal. This is the operator's actual problem and is sufficient to establish the incident.

Evidence: keep detailed timestamps, source lag, duplicate observations, consumer checkpoint disagreement and cleanup preview in `/app/continuity/log/archive` and `/app/continuity/ops`. The instruction should point to those artifacts instead of narrating them.

Shared context: record layouts, identity fields, generation semantics, replay eligibility and retention watermark rules belong in `/app/continuity/docs/continuity-contract.md`. They are legitimate system contracts, not prose to duplicate in the handoff.

Expected outcome: archive convergence exactly once by stable event identity, crash/reconnect-safe consumer progress, held generation ambiguity and safe retention. These are grouped operational invariants rather than one sentence per hidden test.

Uncertainty/asymmetry: the operator knows the reconnect happened and has observed duplicate effects/checkpoint disagreement, but does not assert a root cause or implementation. The instruction should preserve that diagnostic boundary.

## Jira/Slack handoff check

PASS. The current instruction reads as an incident handoff: symptom, evidence locations, desired reliability and two easy-to-miss constraints. It does not enumerate the 26 private manifestations or 28 F2P tests.

## Reverse-outline check

LOW risk. Paragraph one is incident/evidence; paragraph two is the operational end state and boundaries. Sentences do not map one-for-one to verifier cases.

## Incident-evidence check

All production claims in the instruction are supported by the archived controller log, shift handoff or stream-state capture. No fabricated customer impact, fake chronology or unsupported operator action is needed.
