# Q8 Aggregate — django-checkout-failover-ha

Diagnostic only. Does **not** replace Harbor GPT×5 or Claude×5 official trials.

| Perspective | Execution | Predicted signal | Result path |
| --- | --- | --- | --- |
| GPT_PERSPECTIVE | SIMULATION_NOT_EXECUTED | USEFUL | `django-checkout-failover-ha-d812d3f7-difficulty-sim-gpt-8788a1f29a.json` |
| CLAUDE_PERSPECTIVE | SIMULATION_NOT_EXECUTED | USEFUL | `django-checkout-failover-ha-d812d3f7-difficulty-sim-claude-87b3953b40.json` |

## Comparison (after both frozen)

- Both perspectives predict **USEFUL** difficulty (coupled fence/router/sticky/readyz/dump/capture).
- GPT prior: symptom-driven local patches; under-fix dump accepting_checkout and capture idempotency after place/pay/readyz look green.
- Claude prior: reconstruct full live-vs-dump matrix first; over-expand into write_policy/heal_plan/cutover_fsm/catalog instead of surgical controlplane+fulfill fixes.
- Neither simulation executed a live verifier; official pass-rate evidence is still required.

## Next

Harbor LLMaJ and official GPT-5.5/Codex ×5 + Claude Opus 4.8 ×5 remain user-deferred. Final Compliance / package wait on that authorization (or an explicit package-only request).
