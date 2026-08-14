# Semantic Authority Trust Root

The Unified Feedback, Remediation & Agent Learning Plane treats repository persistence as attacker-controlled data. Semantic authority is therefore authenticated with detached OpenSSH receipts whose verification keys are outside the repository.

## Production trust store

Production verification is fixed to `/etc/terminus/authority/allowed_signers`.

The file must be root-owned, must not be a symlink, and must not be group/world writable. Repository files and caller-selected environment variables cannot replace this production trust root. `TERMINUS_AUTHORITY_ALLOWED_SIGNERS` is rejected in production.

The allowed-signers file carries the public keys for these principals:

- `terminus-human-authority`
- `terminus-automation-authority`
- `terminus-review-authority`
- `terminus-execution-authority`
- `terminus-finding-authority`
- `terminus-learning-authority`

Private signing keys must remain outside the repository and outside task workspaces.

## Signed semantic actions

Receipts bind the exact JSON claim for one action and principal:

- `HUMAN_FEEDBACK`
- `AUTOMATED_SOURCE`
- `REVIEW_RESULT`
- `EXECUTION_RESULT`
- `FINDING_NORMALIZATION`
- `LESSON_ACTIVATION`

Changing the task, commit, finding/remediation binding, execution outputs, finding semantics, lesson text, or other signed claim material invalidates the receipt.

## Policy conflicts

`POLICY_CONFLICT` admission requires authenticated Adjudicator authority. Each cited rule binds an exact source revision, rule text, rule hash, one shared `decision_key`, `constraint = EQ`, and a scalar `required_value`. The proof must declare `decision_cardinality = EXACTLY_ONE`; at least two exact authoritative rules must impose different values on that same decision.

## Tests

Pytest uses an ephemeral signing key and an external temporary allowed-signers file only when `TERMINUS_AUTHORITY_TEST_MODE=1` and `PYTEST_CURRENT_TEST` is present. This test path is deliberately unavailable as a normal production override.
