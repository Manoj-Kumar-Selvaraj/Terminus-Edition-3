# maven-agent-hop-resume

Local multi-module reactor interpreter with Jenkins-style agent hops, shared-library pins, stash, incremental fingerprints, and crash resume. The starter resumes by rebuilding everything, loads the newest library instead of the pin, will run a maven stage on a docker-only label, and archives plaintext secrets.

## Layout

- `environment/reactor/` — public CLI, contract, crash log, tiny reactor tree, broken interpreter
- `solution/` — corrected engine modules plus `solve.sh` which resumes through `/app/reactor/bin/pipe`
- `tests/` — separate verifier; behavioral F2P/P2P against journal, fingerprints, agents, archive

Difficulty in `task.toml` is provisional until the combined GPT-5.5 ×5 and Claude Opus 4.8 ×5 mean is measured.

## Local Harbor

```bash
stb harbor run -a oracle -p Terminus-Edition-3/maven-agent-hop-resume -o /tmp/e3-maven-jobs
stb harbor run -a nop -p Terminus-Edition-3/maven-agent-hop-resume -o /tmp/e3-maven-jobs
```
