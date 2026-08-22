# Q7 Task Format Enforcer — jenkins-home-insights-plugin

```text
STATUS: FORMAT_PASS
TASK_COMMIT: untracked (local tree; not yet committed)
CHECKS:
- RULE: flat Edition 3 layout
  PATH: jenkins-home-insights-plugin/
  EXPECTED: task.toml, instruction.md, README.md, environment/, solution/solve.sh, tests/
  OBSERVED: present; no milestones/rubrics/generated jobs inside task root
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: task.toml canonical fields
  PATH: jenkins-home-insights-plugin/task.toml
  EXPECTED: version 2.0, artifacts top-level, environment_mode=separate, agent timeout 1800-18000, network public
  OBSERVED: artifacts=["/app/plugin"], environment_mode=separate, agent timeout_sec=7200, network_mode=public, memory_mb=8192
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: digest-pinned Maven base + tmux/asciinema
  PATH: jenkins-home-insights-plugin/environment/Dockerfile
  EXPECTED: maven:3.9.9-eclipse-temurin-21@sha256:3a4ab327…; tmux; asciinema; agent stays alive for Harbor
  OBSERVED: canonical digest; tmux; asciinema; bake generate/reconcile; CMD sleep infinity; bin scripts via sh
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: separate verifier image
  PATH: jenkins-home-insights-plugin/tests/Dockerfile
  EXPECTED: separate image; pytest lockfile; no /logs/verifier at build; no solution copy
  OBSERVED: canonical Python digest; pip from requirements.lock; copies test.sh + test_outputs.py; mkdir only /app/plugin /tests
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: tests/test.sh reward contract
  PATH: jenkins-home-insights-plugin/tests/test.sh
  EXPECTED: mkdir /logs/verifier at runtime; write reward after pytest; install nothing; no trailing exit
  OBSERVED: mkdir; echo 0 then 1/0; LF shebang
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: shell scripts LF
  PATH: solution/solve.sh, tests/test.sh, environment/plugin/bin/*
  EXPECTED: Unix LF shebang
  OBSERVED: converted; .gitattributes forces eol=lf on *.sh and plugin/bin/*
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: environment/.dockerignore
  PATH: jenkins-home-insights-plugin/environment/.dockerignore
  EXPECTED: exclude git, caches, solution/, tests/, target/
  OBSERVED: present; **/target/ excluded
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: no build output in task tree
  PATH: environment/plugin/target/
  EXPECTED: no committed build artifacts
  OBSERVED: stray core-sources.txt removed
  CLASS: DETERMINISTIC
  ACTION: removed core-sources.txt
- RULE: no .terminus leakage in package
  PATH: jenkins-home-insights-plugin/
  EXPECTED: no private control-plane paths inside task zip root
  OBSERVED: none
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: ruff on verifier tests
  PATH: jenkins-home-insights-plugin/tests/test_outputs.py
  EXPECTED: ruff clean
  OBSERVED: All checks passed (ruff 0.8.4)
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: large_system_strict F2P range
  PATH: tests + test-map
  EXPECTED: 25-30 F2P; map matches names
  OBSERVED: 30 F2P / 4 P2P; validate_task_complexity PASS
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: instruction length and schema
  PATH: jenkins-home-insights-plugin/instruction.md
  EXPECTED: ≤20 bullets; absolute paths; no solution walkthrough
  OBSERVED: 20 bullets; /app/plugin paths; contract references only
  CLASS: DETERMINISTIC
  ACTION: none
RERUN: Harbor oracle 1.0 (2026-08-22__13-17-32, 34/34); Harbor NOP 0.0 (2026-08-22__13-20-18, 20 fail / 14 pass, all P2P pass)
NOTE: Use stb-bundled Harbor 0.21 for environment_mode=separate on Windows; system pip harbor 0.5.x is incompatible.
```
