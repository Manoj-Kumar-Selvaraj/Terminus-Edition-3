# Q7 Task Format Enforcer — event-time-session-window-processor

```text
STATUS: FORMAT_PASS
TASK_COMMIT: PENDING_FREEZE
CHECKS:
- RULE: flat Edition 3 layout
  PATH: event-time-session-window-processor/
  EXPECTED: task.toml, instruction.md, README.md, environment/, solution/solve.sh, tests/
  OBSERVED: present; no milestones/rubrics/generated jobs
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: task.toml canonical fields
  PATH: event-time-session-window-processor/task.toml
  EXPECTED: version 2.0, artifacts top-level, environment_mode=separate, agent timeout 1800-18000, network public
  OBSERVED: artifacts=["/app/sessions"], environment_mode=separate, agent timeout_sec=7200, network_mode=public, memory_mb=8192
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: digest-pinned Python base + tmux/asciinema
  PATH: event-time-session-window-processor/environment/Dockerfile
  EXPECTED: python:3.13-slim-bookworm@sha256:01f42367…; tmux; asciinema; no recursive chmod /app
  OBSERVED: canonical digest; tmux; asciinema; chmod only bin + generate_seed.py
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: separate verifier image
  PATH: event-time-session-window-processor/tests/Dockerfile
  EXPECTED: separate image; pytest lockfile; no /logs/verifier at build; no solution copy
  OBSERVED: same digest; pip from requirements.lock; copies test.sh, test_outputs.py, fixtures/
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: tests/test.sh reward contract
  PATH: event-time-session-window-processor/tests/test.sh
  EXPECTED: mkdir /logs/verifier at runtime; write reward after pytest; install nothing; no trailing exit
  OBSERVED: mkdir; echo 0 then 1/0; LF shebang after Q5 CRLF repair
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: shell scripts LF
  PATH: solution/solve.sh, tests/test.sh, environment/sessions/bin/run-sessions
  EXPECTED: Unix LF shebang
  OBSERVED: converted; task .gitattributes forces eol=lf
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: no .terminus leakage in package
  PATH: event-time-session-window-processor/
  EXPECTED: no private control-plane paths inside task zip root
  OBSERVED: none
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: ruff on verifier tests
  PATH: event-time-session-window-processor/tests/test_outputs.py
  EXPECTED: ruff clean
  OBSERVED: All checks passed
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: large_system_strict F2P range
  PATH: tests + test-map
  EXPECTED: 25-30 F2P; map matches names
  OBSERVED: 25 F2P / 11 P2P; validate_task_complexity PASS (seed.sql dominates LOC)
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: environment/.dockerignore
  PATH: event-time-session-window-processor/environment/.dockerignore
  EXPECTED: exclude git, caches, solution/, tests/; do not exclude required .log evidence
  OBSERVED: present; *.log not excluded so processor-bounce.log ships
  CLASS: DETERMINISTIC
  ACTION: none
RERUN: Harbor oracle 1.0 (2026-08-17__12-13-37); Harbor NOP 0.0 (2026-08-17__12-14-37)
```
