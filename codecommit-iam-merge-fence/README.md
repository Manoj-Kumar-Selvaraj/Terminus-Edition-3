# codecommit-iam-merge-fence

Local CodeCommit platform control plane: IAM evaluation, PR quorum, fast-forward merge fence, exactly-once pipeline journal, authz audit log, and webhook outbox — exposed through CLI and HTTP API.

## Why it is hard

Clone/push/merge/deliver/API share one evaluator. Prefix action matching, skipped MFA/CIDR/Deny, broken quorum math, non-FF merges, random event ids, missing audit denies, and API IAM bypass interact. Fixing one plane still fails the contract.

## Solution approach

Repair the Python control plane under `/app/codecommit` so CLI and API honor the contract. The oracle replaces the broken modules under `lib/cc`.

## Verification

Separate verifier drives `ccctl` against a private `CC_ROOT`, checking authz, FF merge, journal identity, audit, and outbox behavior.
