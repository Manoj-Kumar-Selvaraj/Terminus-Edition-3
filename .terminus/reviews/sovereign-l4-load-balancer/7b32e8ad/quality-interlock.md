# Quality Interlock — sovereign-l4-load-balancer @ 7b32e8ad

```text
QUALITY_INTERLOCK: REVISE
TASK_COMMIT: 7b32e8ad4974a4d8012085b08d82a9b1f9ca5579
ISOLATION: PROCEDURAL cold review via isolated subagents (Q4 + Q6)
Q4: REVISE (HIGH, SUFFICIENT) sovereign-l4-load-balancer-7b32e8ad-spec-test-contract-19bf052a7a
Q4_PATH: .terminus/reviews/sovereign-l4-load-balancer/7b32e8ad/sovereign-l4-load-balancer-7b32e8ad-spec-test-contract-19bf052a7a.json
Q4_BLOCKING: Q4-B01..Q4-B06
Q4_ADVISORY: Q4-A01, Q4-A02
Q4_SUBAGENT: b0fbb074-1256-4d85-bc35-067d02abec77
Q4_ATTEMPTS: 3/3 durable budget (d7a001a9 REVISE, 13ffb6b2 REVISE, 7b32e8ad REVISE) — do not shop another ordinary Q4 after fix without budget/authority check
Q6: PASS (HIGH, SUFFICIENT) sovereign-l4-load-balancer-7b32e8ad-production-logic-00b7dc11e8
Q6_PATH: .terminus/reviews/sovereign-l4-load-balancer/7b32e8ad/sovereign-l4-load-balancer-7b32e8ad-production-logic-00b7dc11e8.json
Q6_SCOPE_HASH: 5f1cb71bda55b9c1eff62e700975da815c4846c0d812464bb79ba2dd492ca2cf
Q6_REUSE: valid only if production-scope (task.toml+environment/) unchanged; tests/docs/solution-only edits keep Q6 PASS
COMPLEXITY: PASS (f2p_cases=27)
RUNTIME_AUTHENTICITY: PASS
ORACLE/NOP: STALE
PRE_LLMAJ: STALE
SUBMISSION_READY: REVOKED
ROUTE: Q4_REVISE -> Q2 Verifier Coverage + Q3 Spec Ambiguity (connection views)
```

**Q4 blocking remediation**

- B01: Rewrite CURRENT-corrupt F2P to restart/reload dataplane and assert verified-generation fallback
- B02: Prove checkpoint recovery without control republish masking
- B03: Metrics assert zero `generation=` labels (align with observability.md)
- B04: F2P fail_open=true includes unhealthy/ejected targets
- B05: Assert 24-node / three-zone fleet inventory content
- B06: Clarify connection-view contract vs graded status fields (prefer narrow docs to already-graded surfaces)

**Next:** Q2/Q3 producer fixers; keep f2p_cases in 25–30; prefer tests/docs-only so Q6 PASS remains reusable. After fix, Q4 budget is exhausted — use residual-risk acceptance or policy-legal re-entry, not a blind 4th ordinary Q4.
