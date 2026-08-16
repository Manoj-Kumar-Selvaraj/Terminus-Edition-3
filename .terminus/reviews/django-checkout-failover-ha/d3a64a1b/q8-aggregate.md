# Q8 Aggregate — django-checkout-failover-ha

Diagnostic only. Does **not** replace Harbor GPT×5 or Claude×5 official trials.

| Perspective | Execution | Predicted signal | Result path |
| --- | --- | --- | --- |
| GPT_PERSPECTIVE | SIMULATION_NOT_EXECUTED | USEFUL | `django-checkout-failover-ha-d3a64a1b-difficulty-sim-gpt-e37a9a5deb.json` |
| CLAUDE_PERSPECTIVE | SIMULATION_NOT_EXECUTED | USEFUL | `django-checkout-failover-ha-d3a64a1b-difficulty-sim-claude-0213591303.json` |

## Comparison (after both frozen)

- Both perspectives predict **USEFUL** difficulty (fence/router/sticky/readyz/dump/capture coupling).
- GPT prior: symptom-driven local patch loop; stop after dump/curl look green while pins/accepting_checkout/repeat_captures still wrong.
- Claude prior: full contract matrix first; over-expand into catalog/FSM helpers instead of surgical fence+sticky+readyz+capture fixes.
- Neither simulation executed a live verifier; official pass-rate evidence is still required.

## Next

Harbor LLMaJ and official GPT-5.5/Codex ×5 + Claude Opus 4.8 ×5 remain user-deferred. Final Compliance / package wait on that authorization (or an explicit package-only request).
