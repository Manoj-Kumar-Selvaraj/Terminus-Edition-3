# codecommit-iam-merge-fence

Local CodeCommit stand-in: IAM-like policy evaluation over git file remotes, PR approval quorum, fast-forward-only merge, and an exactly-once CodePipeline trigger journal.

## Why it is hard

Clone, push, merge, and deliver share one evaluator. A `*` action, ignored MFA/CIDR, prefix-matched Git verbs, and skipped explicit Deny interact with quorum math and merge topology. Fixing only the journal still lets a non-FF merge or an MFA-less main push through.

## Solution approach

Repair the Python evaluator, merge path, approval accounting, and trigger journal under `/app/codecommit`. The oracle copies the corrected modules and leaves repos reachable through `ccctl`.

## Verification

Separate verifier image with git + pytest. Tests build a private `CC_ROOT`, drive `ccctl`, and check authz decisions, ref ancestry, and journal identity. Difficulty in `task.toml` is provisional until both model families are measured.
