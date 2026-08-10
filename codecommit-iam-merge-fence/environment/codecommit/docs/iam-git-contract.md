# Local CodeCommit IAM + merge fence

Operator binary: `/app/codecommit/bin/ccctl`. Policy documents: `/app/codecommit/policies/*.json`. Principal attachments: `/app/codecommit/ops/principals.json`. Approval rules: `/app/codecommit/ops/approval-rules.json`. Pipeline bindings: `/app/codecommit/ops/pipelines.json`. Bare repos: `/app/codecommit/var/repos/<name>.git`. Pull-request store: `/app/codecommit/var/prs.json`. Trigger journal: `/app/codecommit/var/triggers.jsonl`.

## Identity flags

`--principal NAME` is required. `--mfa` sets `aws:MultiFactorAuthPresent` true (absent = false). `--source-ip ADDR` sets `aws:SourceIp` (default `127.0.0.1`). Unknown principals fail `{"error":"AccessDenied","code":"UNKNOWN_PRINCIPAL"}`.

## Commands

```
ccctl --principal NAME [--mfa] [--source-ip ADDR] clone REPO DEST
ccctl --principal NAME [--mfa] [--source-ip ADDR] push REPO WORKTREE BRANCH
ccctl --principal NAME [--mfa] [--source-ip ADDR] pr REPO --source SRC --dest DST
ccctl --principal NAME [--mfa] [--source-ip ADDR] approve REPO PR_ID
ccctl --principal NAME [--mfa] [--source-ip ADDR] merge REPO PR_ID
ccctl --principal NAME [--mfa] [--source-ip ADDR] deliver REPO REF
```

Success (except `clone`, which is silent git output plus a final JSON line) prints one JSON object on stdout and exits 0. Failures print one JSON object on stderr and exit 1.

`clone` requires `codecommit:GitPull` on `refs/heads/<default>` where default is `main` if present else the bare repo HEAD. It clones the bare repo into DEST (DEST must not exist).

`push` requires `codecommit:GitPush` on `refs/heads/BRANCH` (BRANCH may be passed with or without the `refs/heads/` prefix; evaluation always uses the full ref). It pushes WORKTREE's BRANCH to origin.

`pr` opens a pull request from SRC to DST (full refs stored). Author is the caller. Prints `{"ok":true,"pr_id":int,"source":str,"dest":str,"source_commit":str}`. Does not change git refs. Requires `codecommit:GitPull` on the source ref.

`approve` records the caller on that PR. Prints `{"ok":true,"pr_id":int,"approvals":[str,...]}` sorted. Does not require an IAM git action; the caller must exist. Duplicate principal names appear at most once in the stored list.

`merge` requires `codecommit:MergePullRequestByFastForward` on the destination ref. It succeeds only when:

1. The PR is open.
2. Distinct approvals from the destination rule's `pool`, excluding the PR author, are at least `required`.
3. Destination HEAD is an ancestor of source HEAD (fast-forward). The dest ref is then updated to the source commit. No merge commit is created.

Prints `{"ok":true,"pr_id":int,"commit":str,"fast_forward":true}`.

`deliver` loads pipeline bindings for exact `(repo, ref)`. For each binding it writes at most one journal object for `(repo, ref, commit, pipeline)` where commit is the current ref tip. `event_id` is the lowercase hex sha256 of `repo|ref|commit|pipeline` UTF-8. A repeat call must not append another line; it prints `{"ok":true,"delivered":[...],"duplicate":true}` when every binding was already present. First success uses `"duplicate":false`. Each delivered element is `{"event_id":str,"repo":str,"ref":str,"commit":str,"pipeline":str,"status":"delivered"}`.

## IAM evaluation

Default deny. Attachments listed on the principal are the only policy files loaded (`/app/codecommit/policies/<id>.json`). Each file is a document with `Statement` array.

A statement matches when Action, Resource, and every Condition operator succeed.

Action: exact `codecommit:GitPull`, `codecommit:GitPush`, `codecommit:MergePullRequestByFastForward`, or `*` / `codecommit:*` meaning those three only. `*` does not waive Resource or Condition.

Resource: exact ARN `arn:local:codecommit:local:000000000000:<repo>` or a suffix `*` wildcard. `*` as Action still requires this Resource match.

Condition operators (all keys AND):

- `StringEquals` — context value equals the string or is a member of the list.
- `Bool` — context bool equals the policy value (`"true"` / `"false"`). Missing context key fails the statement.
- `IpAddress` — `aws:SourceIp` is inside the CIDR (or any CIDR in a list). Missing source IP fails the statement.

`codecommit:References` is the full ref (`refs/heads/main`). Explicit `Deny` matching statements win over `Allow`. No matching Allow is deny: `{"error":"AccessDenied"}`.

## Approval rules

`/app/codecommit/ops/approval-rules.json`:

```
{"rules":[{"repo":str,"destination":str,"required":int,"pool":[str,...]}]}
```

The rule whose `repo` and `destination` match the PR dest applies. If none matches, merge fails `{"error":"ValidationException","code":"NO_APPROVAL_RULE"}`. Author cannot satisfy quorum. Principals outside `pool` are ignored. Same principal counted once.

## Pipeline bindings

```
{"bindings":[{"repo":str,"ref":str,"pipeline":str}]}
```

`deliver` on a ref with no bindings prints `{"ok":true,"delivered":[],"duplicate":false}` and writes nothing.

## Journal line schema

One JSON object per line, keys in this order: `event_id`, `repo`, `ref`, `commit`, `pipeline`, `status`. `status` is always `delivered`.

## Git identity

Commits created by helper seed paths use `CodeCommit Lab <lab@local>` and timestamp `2026-04-01T12:00:00+0000`. Agent repairs may keep whatever committer the workflow already uses; tests set dates themselves when they create commits.
