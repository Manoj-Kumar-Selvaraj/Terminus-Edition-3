# CodeCommit platform control plane contract

Operator CLI: `/app/codecommit/bin/ccctl`. HTTP API: `/app/codecommit/bin/cc-api`.
Policies: `/app/codecommit/policies/*.json`. Principal attachments: `/app/codecommit/ops/principals.json`.
Approval rules: `/app/codecommit/ops/approval-rules.json`. Pipeline bindings: `/app/codecommit/ops/pipelines.json`.
Webhooks: `/app/codecommit/ops/webhooks.json`. Bare repos: `/app/codecommit/var/repos/<name>.git`.
PR store: `/app/codecommit/var/prs.json`. Trigger journal: `/app/codecommit/var/triggers.jsonl`.
Audit log: `/app/codecommit/var/audit.jsonl`. Webhook outbox: `/app/codecommit/var/outbox.jsonl`.

## Identity

`--principal NAME` required. `--mfa` sets `aws:MultiFactorAuthPresent` true (absent = false).
`--source-ip ADDR` sets `aws:SourceIp` (default `127.0.0.1`).
Unknown principals fail `{"error":"AccessDenied","code":"UNKNOWN_PRINCIPAL"}`.

HTTP headers: `X-Principal`, `X-MFA`, `X-Source-Ip` with the same semantics.

## CLI commands

```
ccctl --principal NAME [--mfa] [--source-ip ADDR] clone REPO DEST
ccctl --principal NAME [--mfa] [--source-ip ADDR] push REPO WORKTREE BRANCH
ccctl --principal NAME [--mfa] [--source-ip ADDR] pr REPO --source SRC --dest DST
ccctl --principal NAME [--mfa] [--source-ip ADDR] approve REPO PR_ID
ccctl --principal NAME [--mfa] [--source-ip ADDR] merge REPO PR_ID
ccctl --principal NAME [--mfa] [--source-ip ADDR] deliver REPO REF
```

Success prints one JSON object on stdout (clone is silent except errors). Failures print one JSON object on stderr and exit 1.

Push success: `{"ok":true,"repo":str,"ref":str,"commit":str}` with full `refs/heads/...` ref.
Approve success: `{"ok":true,"pr_id":int,"approvals":[str,...]}` sorted, principal at most once.
Merge success: `{"ok":true,"pr_id":int,"commit":str,"fast_forward":true}`.

## IAM evaluation

Default deny. Load only attached policy files. Statement matches when Action, Resource, and every Condition succeed.
Action: exact `codecommit:GitPull`, `codecommit:GitPush`, `codecommit:MergePullRequestByFastForward`, or `*` / `codecommit:*` meaning those three only. `*` does not waive Resource or Condition.
Resource: exact ARN or suffix `*`. Explicit Deny matching statements win over Allow.
Conditions (AND):
- `StringEquals` — equality or membership in a list
- `Bool` — missing context key fails
- `IpAddress` — CIDR membership; missing source IP fails
`codecommit:References` is the full ref.

## Approvals and merge

Rule match on repo + destination. Missing rule => `NO_APPROVAL_RULE`.
Insufficient distinct in-pool approvals (author excluded, duplicates once) => `APPROVAL_QUORUM`.
Merge requires `MergePullRequestByFastForward` on dest. Fast-forward only; else `NOT_FAST_FORWARD`. Dest updated to source commit; no merge commit.

## Deliver and outbox

`deliver` normalizes REF like push (`refs/heads/` optional) before binding lookup and event_id preimage.
`event_id` = sha256 hex of `repo|ref|commit|pipeline` UTF-8.
Journal line keys in order: `event_id`, `repo`, `ref`, `commit`, `pipeline`, `status`.
Exactly once per repo/ref/commit/pipeline. Repeat returns `duplicate:true` without appending.
Successful first deliver also enqueues webhook outbox rows for matching webhook configs.
Outbox failed rows may be retried until max attempts.

## Audit

Every authorize decision (allow and deny) appends to `/app/codecommit/var/audit.jsonl`.
