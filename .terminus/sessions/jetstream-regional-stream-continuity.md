# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `task/jetstream-quality-interlock`
- Pull request: `#12`
- Current task commit: `440aa83862a3234678e27bd70319623735964173`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | solver-visible contract unchanged by closure; prior Q4 findings were verifier-coverage gaps |
| Q2 Verifier Coverage Repair | PASS | consolidated repair task commit `440aa83862a3234678e27bd70319623735964173` |
| Q3 Spec Ambiguity Repair | PASS | solver-visible contract unchanged; no grading-relevant ambiguity introduced |
| Q7 Task Format Enforcer | PASS | no package-format change; fresh package-isolation validation below |
| Creator Complexity Gate | PASS | run `31332216483` |
| Preflight/static | PASS | Edition-3 run `31332216470`, job `93292224707` |
| Ruff verifier | PASS | Edition-3 run `31332216470`, job `93292224707` |
| STB auth/AI credentials | FAIL | credential preparation failed only after deterministic Oracle/NOP; not freeze evidence |
| Oracle = 1 | PASS | artifact `9043289949`; exactly 40/40 PASS |
| NOP = 0 | PASS | artifact `9043289949`; exactly 30 F2P FAIL + 10 P2P PASS |
| Q4 Spec-Test Contract Reviewer | PENDING | fresh Q4 1.1 packet required for `440aa838...` |
| Q6 Production Logic Auditor | PENDING | fresh Q6 1.1 packet with `review_scope_hash` required for `440aa838...` |
| Quality Interlock | PENDING | requires fresh current-policy Q4 + Q6 PASS |
| Pre-LLMaJ specialist panel | PENDING | not authorized before Quality Interlock PASS |
| Task Architect | PENDING | Stage-B not authorized |
| Verifier Engineer | PENDING | Stage-B not authorized |
| Originality & Authenticity | PENDING | Stage-B not authorized |
| Difficulty design | PENDING | Stage-B not authorized |
| Compliance pre-review | PENDING | Stage-B not authorized |
| Instruction Reviewer | PENDING | Stage-B not authorized |
| Documentation Reviewer | PENDING | Stage-B not authorized |
| Comprehensive Reviewer | PENDING | not authorized |
| Pre-LLMaJ aggregate | PENDING | not authorized |
| Q8 GPT Perspective Simulation | PENDING | not authorized |
| Q8 Claude Perspective Simulation | PENDING | not authorized |
| Harbor LLMaJ | PENDING | not run |
| Difficulty trials | PENDING | not authorized |
| GPT-5.5 difficulty ×5 | PENDING | not authorized |
| Claude Opus 4.8 difficulty ×5 | PENDING | not authorized |
| Combined difficulty ×10 | PENDING | not authorized |
| Per-test solvability 1/10 | PENDING | not authorized |
| Trial Analysis | PENDING | not authorized |
| Final Compliance | PENDING | not authorized |
| Final Human Quality | PENDING | not authorized |
| Final package | PENDING | not authorized |

## Frozen candidate

Exact frozen task commit: `440aa83862a3234678e27bd70319623735964173`.

The closure repairs all three known Q4 verifier-coverage findings in one consolidated cycle without adding tests or weakening preserved behavior:

1. The existing stable-identity F2P now crosses a real edge-west JetStream replay boundary through the real `NatsPublisher`, independently reads stored messages, and requires external `Nats-Msg-Id == event_id`. The recovery-entrypoint P2P remains preservation-only.
2. The existing retention-horizon F2P now separately grades effective durable SQLite journal cleanup age against the full disconnect + replay + safety horizon. The narrow reference repair uses `max(journal_min_age_seconds, required_horizon_seconds)`; starter production code is unchanged so this remains an F2P defect.
3. The existing final-report F2P now requires non-empty timezone-aware parseable `generated_at` values in both `health.json` and `reconciliation.json`, while retaining independent report-truth reconstruction and full captured-incident SHA-256 preservation checks.

The private test map remains exactly 40 mapped tests = 30 F2P + 10 P2P and only REQ-19/REQ-24 descriptions were aligned to the existing solver-visible contract.

## Fresh deterministic evidence

Edition-3 run `31332216470`, job `93292224707` on the repaired task tree:

- Preflight: PASS.
- Ruff verifier tests: PASS.
- verifier/environment setup: PASS.
- Oracle reward: `1`; artifact `9043289949` shows exactly **40 passed** in 22.56s.
- NOP reward: `0`; the same artifact shows exactly **30 failed + 10 passed** in 21.26s.
- Every NOP failure is `test_f2p_*`; every NOP pass is `test_p2p_*`.
- Reusable-AI credential preparation failed only after those deterministic gates; Harbor was skipped and was not used as freeze evidence.
- Validation artifact: `9043289949`, digest `sha256:c355c40a2623398412b120b0915173e14a961e30ba15fe7bbc4e86a40683b84a`.

Additional exact-candidate gates:

- Creator Complexity run `31332216483`: PASS.
- Production Authenticity run `31332216476`: PASS.
- Agent System run `31332216469`, rerun job `93292881604`: PASS, including control-plane regressions, structure, review freshness/commit binding, and package-isolation check.

## Historical review provenance

All Q4/Q6 evidence for `d7e131f962753acce119afba5f63bd525203d9c7` is historical/stale for this candidate. In particular:

- old Q4 commit `d28d169713b5df74755c19037f2dfb79b9e9c08a`: `REVISE/HIGH/SUFFICIENT`; its three coverage findings are the consolidated closure inputs;
- old Q6 commit `d99e501eed8de2d8c83beef9e2f1c18341eb9c99`: `PASS/HIGH/SUFFICIENT`; it predates Q6 1.1 scope-hash provenance and cannot support the current interlock.

## Current-policy review rules

- Fresh Q4 uses role policy 1.1 and must complete the full forward/reverse matrices, delegated-contract/output-interface walks, all F2P/P2P boundaries, and second adversarial omission sweep before returning one exhaustive result with all material findings.
- This closure consumes the one normal consolidated repair/refreeze cycle for the currently known Q4 findings. After the next exhaustive Q4 result, a later finding based entirely on unchanged previously-reviewable evidence is `LATENT_REVIEWER_OMISSION` and routes to Adjudicator before another normal repair loop.
- Fresh Q6 uses role policy 1.1 and must carry `review_scope_hash`; once a new-policy Q6 PASS exists, later verifier-only changes may reuse it only when that production scope hash and role contract are unchanged.

## Next action

Generate exactly one fresh immutable Q4 1.1 packet and one fresh immutable Q6 1.1 packet with repository-native `.terminus/new_review_packet.py`, both bound to task commit `440aa83862a3234678e27bd70319623735964173` and state `FROZEN_CANDIDATE`. Validate packet freshness/binding and package isolation, then run Q4 and Q6 independently in separate cold chats. Do not run Stage-B, Pre-LLMaJ, Q8, Harbor, or model trials until both current-policy reviews PASS and Quality Interlock is validated.
