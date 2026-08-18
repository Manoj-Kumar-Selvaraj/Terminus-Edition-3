# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for StoneVault. Current Git/task-tree/CI/review provenance overrides stale prose or unrelated repository HEAD movement.

## Identity

- Task: `stonevault-crash-safe-storage`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: none
- Current task commit: `29b684f3439269762235665ab2e716da53214c1e`
- Frozen task tree: `33a8b3ea5bce04dff6bfbc7325fc8b1dcccc6424`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Rule Resolution | PASS | current Edition-3 creation policy + Agent System 2.5 reconciled |
| A6 Human Writing Research | PASS | `.terminus/research/stonevault-crash-safe-storage-dataset-calibration.json` + task-writing profile |
| Q1 Spec Gap Repair | PASS | `.terminus/designs/stonevault-crash-safe-storage-spec-alignment.json` |
| Q2 Verifier Coverage Repair | PASS | run `32094975331`; Oracle/NOP empirical matrix over 47 probes |
| Q3 Spec Ambiguity Repair | PASS | pre-freeze producer alignment evidence |
| Q7 Task Format Enforcer | PASS | run `32094975331`, job `95584471150` |
| A9 Assembly | ASSEMBLED | frozen task tree `33a8b3ea5bce04dff6bfbc7325fc8b1dcccc6424` |
| Creator Complexity Gate | PASS | run `32095219892`, job `95585176864`: LOC=3033, F2P cases=25, P2P=19 |
| Runtime Authenticity | PASS | run `32095859763`, job `95586961170`: `production-authenticity gate: PASS` |
| Ruff verifier | PASS | run `32094975331`, job `95584471150` |
| Oracle = 1 | PASS | run `32094975331`, job `95584471150`; 47 passed; artifact `9309650300` |
| NOP = 0 | PASS | run `32094975331`, job `95584471150`; 28 failed / 19 passed |
| Freeze | PASS | exact task tree `33a8b3ea5bce04dff6bfbc7325fc8b1dcccc6424` |
| Q4 Spec-Test Contract Reviewer | REVISE | `.terminus/reviews/stonevault-crash-safe-storage/29b684f3/stonevault-crash-safe-storage-29b684f3-spec-test-contract-0a860fca37.json`; HIGH confidence; SUFFICIENT evidence; blocking `Q4-001`..`Q4-011`, advisory `Q4-012` |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/stonevault-crash-safe-storage/29b684f3/stonevault-crash-safe-storage-29b684f3-production-logic-31d4c38000.json`; HIGH confidence; SUFFICIENT evidence; scope `ffb9c6b644538353bb56f46a761364f697285da48b1d60e8bd16d140fd67ed43` |
| Quality Interlock | BLOCKED | Q6 PASS is current for the frozen production scope, but Q4 requires one consolidated producer repair/refreeze cycle and fresh Q4 |
| Pre-LLMaJ | NOT_REACHED | waits for Quality Interlock |
| Q8 GPT/Claude diagnostics | NOT_REACHED | waits for Pre-LLMaJ |
| Harbor LLMaJ | NOT_REACHED | waits for earlier gates and reusable AI credentials |
| Official model trials | NOT_REACHED | GPT-5.5 x5 + Claude Opus 4.8 x5 only after required preceding gates |
| Difficulty assessment | PROVISIONAL | task.toml `frontier` remains author intent until official trial evidence |
| Submission ready | NO | Q4 remediation and downstream gates remain open |

## Review evidence ledger

| Review | Review ID | Task tree | Protocol | Prompt | Role policy | Scope hash | Result path | Verdict | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q4 Spec-Test Contract Reviewer | `stonevault-crash-safe-storage-29b684f3-spec-test-contract-0a860fca37` | `33a8b3ea5bce04dff6bfbc7325fc8b1dcccc6424` | 2.2 | 2.2 | 1.1 | n/a | `.terminus/reviews/stonevault-crash-safe-storage/29b684f3/stonevault-crash-safe-storage-29b684f3-spec-test-contract-0a860fca37.json` | REVISE | HIGH | 11 blocking findings + 1 advisory; exhaustive bidirectional walk complete |
| Q6 Production Logic Auditor | `stonevault-crash-safe-storage-29b684f3-production-logic-31d4c38000` | `33a8b3ea5bce04dff6bfbc7325fc8b1dcccc6424` | 2.2 | 2.2 | 1.1 | `ffb9c6b644538353bb56f46a761364f697285da48b1d60e8bd16d140fd67ed43` | `.terminus/reviews/stonevault-crash-safe-storage/29b684f3/stonevault-crash-safe-storage-29b684f3-production-logic-31d4c38000.json` | PASS | HIGH | no findings; substantive/reachable production logic confirmed |

## Q4 consolidated remediation boundary

Blocking findings to repair in one producer cycle:

- `Q4-001` remove or legitimize the hidden `flock` mechanism requirement while preserving observable writer exclusion/release.
- `Q4-002` remove undocumented second-writer stderr substring grading while preserving nonzero failure and exclusion.
- `Q4-003` cover the documented default data-directory tier.
- `Q4-004` cover GET-after-own-delete and post-conflict transaction termination.
- `Q4-005` cover acknowledged-COMMIT crash durability and multi-commit WAL replay.
- `Q4-006` cover unknown-type/malformed-payload/impossible-length complete WAL corruption plus independent WAL format compatibility.
- `Q4-007` add a deterministic checkpoint interruption/recovery durability probe without private implementation hooks.
- `Q4-008` make snapshot size checks non-vacuous; isolate duplicate key/oversized value; add independent valid format/CRC compatibility fixture.
- `Q4-009` make HEALTH authority/outcome externally unambiguous and add a meaningful negative invariant case.
- `Q4-010` strengthen C++20/public C ABI/wire-shape preservation semantically rather than source substrings/permissive parsing.
- `Q4-011` add representative cross-command unknown-transaction/key-boundary coverage.
- `Q4-012` advisory: clarify impossible WAL length vs torn-tail semantics if touched by the repair.

## Quality interlock checkpoint

- Frozen candidate reviewed: `29b684f3439269762235665ab2e716da53214c1e`
- Q4: `REVISE`
- Q6: `PASS`
- Quality interlock: `BLOCKED_BY_Q4`
- Next legal action: fresh producer/fixer chat performs a single consolidated Q1/Q2/Q3-aligned remediation, reruns Oracle/NOP and affected deterministic gates, refreezes the new exact task commit, then generates a fresh Q4 packet. Q6 may be reused only if its validated production `review_scope_hash` remains unchanged under the freshness rules; otherwise rerun Q6.

## Circuit breakers

- Status: `CLEAR`
- Trigger: none
- Attempts: 0

## Decisions that must survive chat changes

- Product remains C++20 + Rust only; Python verifier-only; no Go product implementation.
- Pytest function names remain neutral and contain neither `p2p` nor `f2p`; private test map owns classifications.
- Do not weaken legitimate solver-visible behavior merely to make Q4 green.
- Any solver-visible task or verifier change invalidates the old Q4 freeze and requires current Oracle/NOP evidence before refreeze.
- Do not self-issue Q4 or Q6 PASS from the controller chat.
