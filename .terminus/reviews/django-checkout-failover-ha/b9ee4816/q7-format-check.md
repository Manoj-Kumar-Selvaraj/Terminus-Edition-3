# Q7 Task Format Enforcer — django-checkout-failover-ha

```text
STATUS: FORMAT_PASS
TASK_COMMIT: b9ee4816204f1a51857407e4a6f9bf9e38dd937a
CHECKS:
- RULE: flat Edition 3 layout
  PATH: django-checkout-failover-ha/
  EXPECTED: task.toml, instruction.md, README.md, environment/, solution/solve.sh, tests/
  OBSERVED: present
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: task.toml canonical fields
  PATH: django-checkout-failover-ha/task.toml
  EXPECTED: version 2.0, artifacts, verifier.environment_mode=separate, agent timeout 1800-18000, network public
  OBSERVED: artifacts=["/app/ha"], environment_mode=separate, agent timeout_sec=10800, network_mode=public
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: digest-pinned base + tmux/asciinema
  PATH: django-checkout-failover-ha/environment/Dockerfile
  EXPECTED: bookworm-slim digest pin; tmux; asciinema
  OBSERVED: sha256:4724b8cc…; tmux; asciinema installed
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: separate verifier image
  PATH: django-checkout-failover-ha/tests/Dockerfile
  EXPECTED: separate image; pytest; no agent solution copy
  OBSERVED: separate Dockerfile; copies only test_ha.py + test.sh
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: tests/test.sh reward contract
  PATH: django-checkout-failover-ha/tests/test.sh
  EXPECTED: create /logs/verifier; write binary reward after pytest; install nothing
  OBSERVED: mkdir /logs/verifier; reward 0 then 1/0 after pytest
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: no .terminus leakage in package
  PATH: django-checkout-failover-ha/
  EXPECTED: no private control-plane paths inside task zip root
  OBSERVED: none
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: ruff on verifier tests
  PATH: django-checkout-failover-ha/tests/test_ha.py
  EXPECTED: ruff clean
  OBSERVED: All checks passed
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: large_system_strict F2P range
  PATH: tests + test-map
  EXPECTED: 25-30 F2P; map matches names
  OBSERVED: 28 F2P / 6 P2P; validate_task_complexity PASS
  CLASS: DETERMINISTIC
  ACTION: none
RERUN: none
```
