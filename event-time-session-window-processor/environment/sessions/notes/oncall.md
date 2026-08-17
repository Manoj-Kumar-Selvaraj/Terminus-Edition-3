# sessionizer bounce — 17 Aug

Processor came back after the overnight restart and the first replay from collector-b looked fine on acme/u1. The next dump mixed beta traffic into that same user id, and the watermark journal on disk is shorter than the run we thought we persisted.

What we saw:

- late click at t=85000 landed as a new on-time event after a 100000 anchor, then a 1000ms straggler never showed up in late.jsonl
- two tenants sharing user_id=u1 closed as one session
- rerunning the same file with --reset-output wiped watermark.journal even though open_sessions.json still had in-flight keys
- seq in the journal sits at 1 after a few thousand observations

Contract is /app/sessions/docs/session-contract.md. CLI is /app/sessions/bin/run-sessions. Do not blow away /app/sessions/warehouse — that ledger is the production click dump.

Captured log: /app/sessions/logs/processor-bounce.log
