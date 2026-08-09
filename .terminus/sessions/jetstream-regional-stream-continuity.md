# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jetstream-regional-stream-continuity`
- Controller state: `DETERMINISTIC_VALIDATION`
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
| Q1 Spec Gap Repair | PASS | solver-visible contract unchanged by current repair; old Q4 reported coverage gaps, not missing requirements |
| Q2 Verifier Coverage Repair | PASS | consolidated repair commit `440aa83862a3234678e27bd70319623735964173`; closes all three known Q4 coverage findings |
| Q3 Spec Ambiguity Repair | PASS | solver-visible contract unchanged; no grading-relevant ambiguity reported |
| Q7 Task Format Enforcer | PASS | no package-format change in current repair |
| Creator Complexity Gate | PENDING | fresh exact-candidate validation required |
| Preflight/static | PENDING | fresh exact-candidate validation required |
| Ruff verifier | PENDING | fresh exact-candidate validation required |
| STB auth/AI credentials | PENDING | infrastructure dependency; not freeze evidence |
| Oracle = 1 | PENDING | must be exactly 40/40 on `440aa838...` |
| NOP = 0 | PENDING | must remain exactly 30 F2P FAIL + 10 P2P PASS |
| Q4 Spec-Test Contract Reviewer | STALE | all d7e131f9 Q4 evidence predates task repair and current Q4 1.1 contract |
| Q6 Production Logic Auditor | STALE | all d7e131f9 Q6 evidence predates Q6 1.1 scope-hash provenance |
| Quality Interlock | PENDING | deterministic refreeze and fresh Q4/Q6 required |
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

## Consolidated Q4 closure candidate

Repair commit `440aa83862a3234678e27bd70319623735964173` was produced by Agent System run `31332123297`, job `93291929858`; every repair-job step passed, including exact frozen-baseline verification, deterministic patching, Python compile checks, the static 40-test / 30-F2P / 10-P2P shape check, and self-cleanup of temporary orchestration files.

The repair is intentionally narrow:

1. Existing F2P stable-identity coverage now crosses a real edge-west JetStream replay boundary with the real `NatsPublisher`, reads stored messages externally, and requires physical `Nats-Msg-Id` to equal payload `event_id` for each expected replay identity. The preserved recovery CLI P2P was not strengthened, avoiding the previous 31/9 NOP partition failure.
2. Existing F2P retention coverage now separately proves durable SQLite journal cleanup preserves a row still inside the full disconnect + replay + safety recovery horizon while allowing a sufficiently old safe row. The reference engine receives the narrow corresponding fix by using the larger of minimum journal age and required recovery horizon; starter runtime code is unchanged.
3. Existing report F2P now requires non-empty, timezone-aware parseable `generated_at` values in both `health.json` and `reconciliation.json`, while retaining independent truth reconstruction and full captured-evidence digest checks.
4. Private REQ-19/REQ-24 test-map descriptions were aligned with the already solver-visible contract; no new tests were added.

## Historical baseline

The previous frozen task commit `d7e131f962753acce119afba5f63bd525203d9c7` had Oracle exactly 40/40 and NOP exactly 30 F2P FAIL + 10 P2P PASS in Edition-3 run `31327893697`, artifact `9042083147`; Complexity `31327893703`, Production Authenticity `31327893712`, and Agent System/package isolation `31327893701` passed. Harbor was not run.

Historical Q4 result commit `d28d169713b5df74755c19037f2dfb79b9e9c08a` was `REVISE/HIGH/SUFFICIENT` with the three coverage findings now addressed. Historical Q6 result commit `d99e501eed8de2d8c83beef9e2f1c18341eb9c99` was `PASS/HIGH/SUFFICIENT` with no findings. Both are stale for current acceptance.

## Circuit breaker / no-drip state

- Old repeated narrow Q4 patch-loop strategy remains retired.
- This is the single consolidated repair/refreeze cycle for the currently known findings.
- After refreeze, Q4 1.1 must perform its exhaustive one-pass audit and return all material findings together.
- After that exhaustive Q4 cycle, any later finding resting entirely on unchanged previously-reviewable evidence is classified `LATENT_REVIEWER_OMISSION` and routed to Adjudicator before another normal repair loop.
- Fresh Q6 1.1 must record `review_scope_hash`; once a new-policy Q6 PASS exists, later verifier-only changes may reuse it only when the production scope hash and role contract remain unchanged.

## Next action

Run fresh deterministic validation for exact task commit `440aa83862a3234678e27bd70319623735964173`. Freeze only if Preflight, Ruff, verifier setup, Oracle exactly 40/40, NOP exactly 30 F2P FAIL + 10 P2P PASS, Creator Complexity, Production Authenticity, and Agent System/package isolation all pass. Then generate one fresh Q4 1.1 packet and one fresh Q6 1.1 packet for the same frozen task commit. Do not run Stage-B, Harbor or model trials before current-policy Quality Interlock PASS.
