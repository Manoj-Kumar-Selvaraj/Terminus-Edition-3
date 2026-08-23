# Quality Interlock — jenkins-home-insights-plugin @ 0766c0a2

```text
QUALITY_INTERLOCK: FAIL
TASK_COMMIT: 0766c0a2cb6b666c72f111ef49f3a8724d46ba42
ISOLATION: AUTOMATED cold subagents (Q4 and Q6 parallel; PROCEDURAL)
Q4: REVISE (HIGH, SUFFICIENT) jenkins-home-insights-plugin-0766c0a2-spec-test-contract-7aafeea56c
Q4_PATH: .terminus/reviews/jenkins-home-insights-plugin/0766c0a2/jenkins-home-insights-plugin-0766c0a2-spec-test-contract-7aafeea56c.json
Q4_BLOCKING: Q4-B01 torn journal-prefix; Q4-B02 contains filter; Q4-B03 query metadata; Q4-B04 env path overrides; Q4-B05 HTTP unauthorized rejection
Q4_ADVISORY: Q4-A01 default generate 14536; Q4-A02 queue ageMillis
Q6: PASS (HIGH, SUFFICIENT) jenkins-home-insights-plugin-0766c0a2-production-logic-63d408fd36
Q6_PATH: .terminus/reviews/jenkins-home-insights-plugin/0766c0a2/jenkins-home-insights-plugin-0766c0a2-production-logic-63d408fd36.json
Q6_SCOPE_HASH: 6a41990f5457a68654f5f310e20d218e2a693be88a9844038392e7732b56a58f
Q7: FORMAT_PASS .terminus/reviews/jenkins-home-insights-plugin/q7-format-check.md
ORACLE: 1.0 jobs/2026-08-22__13-17-32 (34/34)
NOP: 0.0 jobs/2026-08-22__13-20-18 (20 fail / 14 pass)
PRE_LLMAJ: BLOCKED until Q4 PASS
NEXT: Verifier Author — add behavioral probes for Q4-B01..B05; rerun oracle/NOP; regenerate Q4 packet
```
