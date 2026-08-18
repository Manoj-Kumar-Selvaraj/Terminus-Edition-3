# FORMAT_GATE — yard-gate-dock-dwell-control

```text
STATUS: PASS
FOLDER: kebab-case matches task.toml name
TASK_TOML: Operations/Logistics; artifacts top-level ["/app/yard"]; environment_mode=separate; agent timeout 7200; network public
DOCKER: agent and verifier digest-pinned python:3.13-slim-bookworm canonical; tmux+asciinema in agent; verifier bakes pytest pins; mkdir /app/yard/out /app/yard/var
TEST_SH: canonical reward pattern; no pip; no trailing exit
SOLVE_SH: copies fixed modules; does not special-case verifier
ISOLATION: .dockerignore excludes solution/tests; agent image seeds at build
INSTRUCTION: 10 bullets; absolute paths; incident evidence named
```
