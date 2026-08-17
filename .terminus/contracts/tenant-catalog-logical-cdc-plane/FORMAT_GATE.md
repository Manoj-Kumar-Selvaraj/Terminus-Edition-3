# FORMAT_GATE — tenant-catalog-logical-cdc-plane

```text
STATUS: FORMAT_PASS
CHECKS:
- RULE: flat Edition 3 layout
  PATH: tenant-catalog-logical-cdc-plane/
  EXPECTED: task.toml, instruction.md, README.md, environment/, solution/, tests/
  OBSERVED: present
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: task.toml taxonomy/artifacts/environment_mode
  PATH: task.toml
  EXPECTED: Software/Databases; artifacts=["/app/catalog"]; environment_mode=separate; languages go/sql/bash
  OBSERVED: matches
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: digest-pinned agent/verifier images + tmux/asciinema
  PATH: environment/Dockerfile, tests/Dockerfile
  EXPECTED: pinned digests; agent has tmux+asciinema; Go 1.24 bookworm agent; Python verifier-only
  OBSERVED: matches
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: .dockerignore excludes solution/tests
  PATH: environment/.dockerignore
  EXPECTED: solution/ and tests/ excluded
  OBSERVED: matches
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: tests/test.sh reward contract
  PATH: tests/test.sh
  EXPECTED: create /logs/verifier; always write binary reward after pytest; LF shebang
  OBSERVED: matches
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: solution/solve.sh oracle path
  PATH: solution/solve.sh
  EXPECTED: deterministic copy of fixed Go packages + rebuild + public CLI; LF shebang
  OBSERVED: matches
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: no agent-visible Python catalog logic
  PATH: environment/catalog
  EXPECTED: no *.py under agent tree
  OBSERVED: none
  CLASS: DETERMINISTIC
  ACTION: none
RERUN: validators ruff/complexity/authenticity PASS locally
```
