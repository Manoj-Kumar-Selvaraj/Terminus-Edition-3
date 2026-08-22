# Reference solution

`solve.sh` applies `repair.py` to `/app/sovereign-lb`, then rebuilds all binaries with `bin/build`.

The repair script fixes cross-language canonical prepare digests, revision digest fencing, connected rollout quorum counting, readiness gating, drain transitions on activate, eligibility fail-open behavior, passive health hooks, checkpoint generation naming, and torn-frame rejection without exposing private defect identifiers.

Run inside the agent image:

```bash
/solution/solve.sh
```
