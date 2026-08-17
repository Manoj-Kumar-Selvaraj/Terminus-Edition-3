# Q8 Aggregate — event-time-session-window-processor

Diagnostic only. Does **not** replace Harbor GPT×5 or Claude×5 official trials.

| Perspective | Execution | Predicted signal | Result path |
| --- | --- | --- | --- |
| GPT_PERSPECTIVE | SIMULATION_NOT_EXECUTED | USEFUL | `event-time-session-window-processor-3fec54c6-difficulty-sim-gpt-8aad19f50c.json` |
| CLAUDE_PERSPECTIVE | SIMULATION_NOT_EXECUTED | USEFUL | `event-time-session-window-processor-3fec54c6-difficulty-sim-claude-85f1de1cc0.json` |

## Comparison (after both frozen)

- Both perspectives predict **USEFUL** difficulty on freeze `3fec54c`.
- GPT prior: grep oncall/log then patch tenant key, journal seq, `--reset-output`, and stop after a local micro-repro looks green while watermark order / event-time gap remain half-fixed.
- Claude prior: reconstruct the full session-contract matrix first; risk of over-scoping catalog/CLI helpers instead of the coupled watermark-journal-lateness-tenant defects.
- Neither simulation executed a live Harbor verifier; official pass-rate evidence is still required.

## Next

Harbor LLMaJ and official GPT-5.5 ×5 + Claude Opus 4.8 ×5 remain user-deferred unless asked.
