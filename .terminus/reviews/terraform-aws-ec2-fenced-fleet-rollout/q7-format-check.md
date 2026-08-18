# Q7 Task Format Enforcer — terraform-aws-ec2-fenced-fleet-rollout

```text
STATUS: FORMAT_PASS
TASK_COMMIT: 1320dba179b9dc7f4d44c6de5b8e6a052180d031
CHECKS:
- RULE: flat Edition 3 layout
  PATH: terraform-aws-ec2-fenced-fleet-rollout/
  EXPECTED: task.toml, instruction.md, README.md, environment/, solution/solve.sh, tests/
  OBSERVED: present; no milestones/rubrics/generated jobs inside the task tree
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: task.toml canonical fields
  PATH: terraform-aws-ec2-fenced-fleet-rollout/task.toml
  EXPECTED: version 2.0, artifacts top-level, environment_mode=separate, agent timeout 1800-18000, network public
  OBSERVED: artifacts include /app/controller /app/internal /app/terraform /app/cmd /app/scripts /app/var/fleet /app/output /app/go.mod /app/go.sum /app/bin; environment_mode=separate; timeout_sec=10800; network_mode=public
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: digest-pinned Go base + tmux/asciinema
  PATH: terraform-aws-ec2-fenced-fleet-rollout/environment/Dockerfile
  EXPECTED: golang:1.24-bookworm@sha256:1a6d4452…; tmux; asciinema; no recursive chmod /app
  OBSERVED: canonical digest; tmux; asciinema; chmod +x operator and go-w on docs/data/evidence/ipam only
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: separate verifier image
  PATH: terraform-aws-ec2-fenced-fleet-rollout/tests/Dockerfile
  EXPECTED: separate image; pytest pins; mkdir artifact parents; no /logs/verifier at build; no solution copy
  OBSERVED: same digest; pip pytest==8.3.5 pytest-json-ctrf==0.5.3 ruff==0.8.4; mkdir /app/{controller,terraform,cmd,internal,var/fleet,output,bin,data,scripts} /tests
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: tests/test.sh reward contract
  PATH: terraform-aws-ec2-fenced-fleet-rollout/tests/test.sh
  EXPECTED: mkdir /logs/verifier at runtime; write reward after pytest; install nothing; no trailing exit
  OBSERVED: canonical reward if/fi; TEST_DIR default /tests
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: shell scripts LF
  PATH: solution/solve.sh, tests/test.sh, environment/bin/fenced-fleet-rollout
  EXPECTED: Unix LF shebang
  OBSERVED: task .gitattributes forces eol=lf for sh/py/Dockerfile/operator
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: no .terminus leakage in package
  PATH: terraform-aws-ec2-fenced-fleet-rollout/
  EXPECTED: no private control-plane paths inside task zip root
  OBSERVED: none
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: ruff on verifier tests
  PATH: terraform-aws-ec2-fenced-fleet-rollout/tests/test_outputs.py
  EXPECTED: ruff clean
  OBSERVED: uvx ruff==0.8.4 All checks passed
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: large_system_strict F2P range
  PATH: tests + test-map
  EXPECTED: 25-30 F2P; map matches names
  OBSERVED: 26 F2P / 2 P2P; validate_task_complexity PASS (substantive_loc=3248)
  CLASS: DETERMINISTIC
  ACTION: none
- RULE: environment/.dockerignore
  PATH: terraform-aws-ec2-fenced-fleet-rollout/environment/.dockerignore
  EXPECTED: exclude git, caches, solution/, tests/; do not exclude required evidence logs
  OBSERVED: removed blanket *.log so evidence/controlplane-lost-reply.log ships
  CLASS: DETERMINISTIC
  ACTION: applied
- RULE: verifier artifact parent dirs
  PATH: tests/Dockerfile
  EXPECTED: mkdir every artifacts[] parent
  OBSERVED: /app/controller terraform cmd internal var/fleet output bin data scripts plus /app via WORKDIR
  CLASS: DETERMINISTIC
  ACTION: none
RERUN: Harbor oracle 1.0 jobs/fleet-rebuild-4/2026-08-17__23-39-25; NOP 0.0 jobs/fleet-nop-2/2026-08-17__23-45-23. Instruction/docs/dockerignore at 1320dba do not change pytest assertions.
```
