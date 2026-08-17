# Q5 Oracle & Runtime Repair — event-time-session-window-processor

```text
STATUS: FIXED
FAILURE_CLASS: APPLICATION/ORACLE + VERIFIER_HARNESS
FIRST_MEANINGFUL_ERROR: /usr/bin/env: 'bash\r': No such file or directory (solve.sh 127); bash: /tests/test.sh: cannot execute: required file not found
ROOT_CAUSE: Windows CRLF shebangs on solution/solve.sh, tests/test.sh, and environment/sessions/bin/run-sessions
FILES_CHANGED: those three scripts converted to LF; task .gitattributes forces eol=lf
INVARIANTS_PRESERVED: oracle copies, verifier assertions, processor semantics unchanged
WHY_TESTS_WERE_NOT_WEAKENED: only line endings
RERUN_GATES: Harbor oracle 1.0 at /tmp/e3-ets/2026-08-17__12-13-37; Harbor NOP 0.0 at /tmp/e3-ets/2026-08-17__12-14-37
REGRESSION_RISK: core.autocrlf on Windows; .gitattributes mitigates
```
