# Terminus Stage Evidence Visibility Policy

Evidence visibility policy version: `1.1`

This policy defines the evidence-class boundary that every registered lifecycle stage must obey. It is a companion to `.terminus/agents/stage_contracts.json`, not a replacement for role contracts, generated review packets, Protocol isolation/freshness rules, or solver-visible task boundaries.

## Purpose

The stage registry answers **what a stage does**. This policy answers **which classes of information the stage may consume or retrieve**.

The canonical machine-readable registry is `.terminus/agents/evidence_visibility.json`, validated against `.terminus/agents/schemas/evidence_visibility.schema.json` by `.terminus/validate_stage_contracts.py`.

Every stage ID in `stage_contracts.json` must have exactly one visibility entry. Every declared evidence class must be classified for that stage as exactly one of:

- `required_evidence_classes` — the stage cannot execute meaningfully without this class;
- `allowed_optional_evidence_classes` — the controller may provide/retrieve this class when useful and permitted;
- `excluded_evidence_classes` — this class must not be supplied or retrieved for the stage unless a narrower higher-precedence role/packet contract explicitly changes the boundary.

The three sets must be disjoint and their union must equal the complete evidence-class registry. There is no implicit/unclassified retrieval bucket.

## Evidence classes

The v1.1 registry distinguishes:

- `CONTROL_PLANE_POLICY` — current authoritative rules, policies, schemas and controller contracts;
- `SOLVER_VISIBLE_TASK` — task material a solver may inspect;
- `PRIVATE_CREATION_DESIGN` — private work-package/design/defect/test-map material;
- `SOLUTION_ORACLE` — reference solution/oracle implementation and solution reasoning;
- `VERIFIER_PRIVATE` — hidden tests/verifier-only expectations and private classification maps;
- `CURRENT_REVIEW_PACKET` — current packet-bound review interface/evidence;
- `PRIOR_REVIEW_RESULTS` — prior/historical semantic verdicts or findings that can contaminate cold review;
- `CI_RUNTIME_EVIDENCE` — commit-bound runs, logs, artifacts, validator output and runtime diagnostics;
- `DURABLE_SESSION_STATE` — reconciled controller/session state and conflict ledger;
- `PUBLIC_REFERENCE` — public/domain/human-writing research treated as evidence, not authority;
- `MODEL_TRIAL_EVIDENCE` — official model trajectories/results and solvability data;
- `FINAL_PACKAGE_EVIDENCE` — package manifests and final submission evidence.

These are control-plane classification labels, not filesystem ACLs. A class label never grants access by itself.

## Precedence and packet isolation

Visibility is intentionally conservative and never weakens a narrower contract.

Apply this order:

`authoritative repository rules -> AGENT_SYSTEM -> PROTOCOL -> role-specific policy -> generated packet allowed/excluded evidence -> stage visibility -> controller convenience`

If a review packet excludes evidence that the stage visibility registry lists as required or optional, the packet exclusion wins. The controller must return `INSUFFICIENT_EVIDENCE` or correct the contract conflict; it must not silently inject excluded evidence.

Likewise, a stage entry cannot make private creator material solver-visible, expose the oracle to the Verifier Author, expose hidden verifier material to a solver simulation, or show prior reviewer verdicts to a cold reviewer.

## Retrieval modes

The registry defines a retrieval mode for future context selection/RAG:

- `EXACT_ONLY` — resolve exact declared files/artifacts/packets first; semantic search is not the default;
- `FILTERED_HYBRID` — exact/structured retrieval may be supplemented by lexical/vector retrieval **only inside the allowed evidence classes**;
- `SOLVER_VISIBLE_ONLY` — retrieval must be confined to `SOLVER_VISIBLE_TASK` plus the minimum control-plane execution contract; no private design, oracle, hidden tests, prior reviews or model-trial evidence;
- `EXTERNAL_BOUND` — execution/evidence is primarily produced by an external evaluation gate; only the declared inputs may be projected into that gate.

RAG, lexical search, vector search or caching must never expand visibility. Retrieval is an optimization inside an already-authorized evidence pool.

## Output disposition

Each stage also classifies the expected disposition of its outputs:

- `EPHEMERAL` — working context that should not become acceptance evidence merely because it exists;
- `DURABLE_CONTROL_PLANE` — durable controller/session/control evidence;
- `PRIVATE_CONTROL_PLANE` — private design/producer evidence not solver-visible;
- `TASK_ARTIFACT` — task/package artifact;
- `REVIEW_EVIDENCE` — packet/result or semantic-review evidence;
- `EXTERNAL_EVIDENCE` — CI/Harbor/model/package evidence produced outside the role's prose response.

Disposition does not itself establish freshness, sufficiency, provenance or PASS. Existing Protocol/schema validation remains mandatory.

## Critical isolation expectations

At minimum:

- `INSTRUCTION_DRAFT` excludes private defect topology, oracle, hidden verifier material and prior review results;
- `VERIFIER_BUILD` excludes the solution/oracle;
- `QUALITY_INTERLOCK` and `PRE_LLMAJ` exclude prior semantic results from cold specialist retrieval unless the applicable adjudication/aggregate role explicitly permits them;
- `MODEL_DIAGNOSTIC` is `SOLVER_VISIBLE_ONLY` and excludes oracle, hidden tests, private creation design, prior reviews and model-trial evidence;
- `OFFICIAL_MODEL_TRIALS` receives the solver-visible task plus only the minimum authoritative/evaluation-bound context;
- review/evaluation stages never infer permission from repository readability alone.

## Retrieval metadata binding

Evidence visibility determines **whether a source class is eligible**. `.terminus/agents/RETRIEVAL_METADATA.md` and `.terminus/agents/retrieval_metadata.json` determine **how an eligible source is identified, versioned, chunked, filtered for freshness, and represented in an index**.

The two contracts must remain separate:

`evidence visibility = authorization boundary`

`retrieval metadata = provenance/indexing envelope`

Retrieval metadata never grants access. A chunk tagged with a permitted stage/role applicability value is still ineligible when its evidence class is excluded by this policy, a narrower role policy, or the active review packet.

`.terminus/validate_retrieval_metadata.py` cross-checks retrieval source profiles and schemas against this evidence-class registry so an indexer cannot silently invent an unclassified evidence category.

## Future RAG requirement

Before vector/semantic RAG is enabled, the retrieval layer must accept at least:

```text
STAGE_ID
ROLE
TASK_COMMIT
CONTROL_PLANE_COMMIT
ALLOWED_EVIDENCE_CLASSES
EXCLUDED_EVIDENCE_CLASSES
ROLE_CONTRACT_HASH / PACKET_BINDING when applicable
```

The retrieval engine must filter by visibility **before** semantic ranking. Post-retrieval filtering alone is insufficient because forbidden material must not enter the candidate context pool for isolated roles.

Caching keys for retrieved context must include the stage/role visibility policy hash and relevant task/control-plane provenance so a cached retrieval cannot survive a visibility or policy change accidentally.
