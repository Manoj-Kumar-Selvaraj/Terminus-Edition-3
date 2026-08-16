# CodeCommit control-plane contract

Applies to the installation rooted at `/app/codecommit`. This document is the
normative description of the plane: the shipped implementation is expected to
match it, not the other way round. Where an operator surface and this contract
disagree, the contract wins.

Root layout:

```
/app/codecommit/bin/ccctl            operator CLI
/app/codecommit/bin/cc-api           HTTP API server
/app/codecommit/lib/cc/              implementation packages
/app/codecommit/docs/                this contract
/app/codecommit/ops/                 principals, approval rules, pipelines, webhooks, shift notes
/app/codecommit/policies/            policy documents, one JSON file per PolicyId
/app/codecommit/log/authz.jsonl      decision extract kept from the previous shift
/app/codecommit/var/                 mutable state (see "State files")
```

`CC_ROOT` overrides the root, so one installation can serve several isolated
roots. Every path below is relative to the active root.

## 1. Identity and request context

A request carries a principal id, an optional MFA assertion, and an optional
source address.

| Surface | Principal | MFA | Source address |
|---|---|---|---|
| `bin/ccctl` | `--principal` | `--mfa` asserts true, `--no-mfa` asserts false, neither asserts nothing | `--source-ip` |
| `bin/cc-api` | `X-Cc-Principal` | `X-Cc-Mfa: true` / `false` | `X-Cc-Source-Ip` |

The evaluated context keys are:

| Key | Value |
|---|---|
| `aws:username` | principal id |
| `cc:Repository` | target repository name, or `*` for plane-wide actions |
| `codecommit:References` | full target ref, present only when the request names one |
| `aws:MultiFactorAuthPresent` | boolean, present only when the caller asserted it |
| `aws:SourceIp` | source address, present only when the caller supplied one |

A context key that the caller did not supply is **absent**. An absent key never
satisfies a condition operator that names it. Headers are read, not verified:
the identity headers assert who is calling and the evaluator decides what that
caller may do.

Ref names are normalized before evaluation, storage, and lookup. `main`,
`heads/main`, and `refs/heads/main` all denote `refs/heads/main`. Only
`refs/heads/*` refs are managed.

## 2. Policy evaluation

A principal's attachments are listed in `ops/principals.json`. Each attachment
names a document `policies/<PolicyId>.json` holding a `Statement` array of
`Sid`, `Effect`, `Action`, `Resource`, and optional `Condition`.

A statement applies to a request when all three hold:

1. **Action** — one `Action` entry covers the requested action. Entries are
   matched in full, case-insensitively, with `*` standing for any run of
   characters and `?` for one character. `*` alone covers every action;
   `codecommit:*` covers every action of that service and no other service's.
2. **Resource** — one `Resource` entry covers the target ARN
   `arn:aws:codecommit:<region>:<account>:<repository>`, with the same wildcard
   rules. A wildcard action does not excuse a statement from matching the
   resource.
3. **Condition** — every operator block holds, and every key inside a block
   holds.

Supported operators:

| Operator | Holds when |
|---|---|
| `StringEquals` | the context value equals one of the listed values |
| `StringNotEquals` | the context value equals none of the listed values |
| `StringLike` | the context value matches one of the listed wildcard patterns |
| `Bool` | the context boolean equals the listed truth value |
| `IpAddress` | the source address is inside one of the listed CIDR blocks |
| `NotIpAddress` | the source address is inside none of the listed CIDR blocks |

An unsupported operator never holds.

Decision order:

1. Unknown principal — the request is denied with reason `unknown_principal`.
2. Any applicable `Deny` statement — denied with reason `explicit_deny`. An
   explicit deny wins over every matching allow, whatever order the
   attachments are listed in.
3. Otherwise any applicable `Allow` statement — allowed with reason
   `allowed_by_policy`, naming the first matching statement.
4. Otherwise denied with reason `no_matching_allow`.

Every evaluated request is recorded (see "State files"). Read-side filtering
that evaluates many resources for one command — `repos list` and
`GET /api/v1/repos` — is not recorded.

Authorization is evaluated at one choke point that both operator surfaces use.
Every mutating operation is authorized: pushing a ref, opening a pull request,
stamping a pull request, landing a pull request, starting a pipeline, and
draining the outbox.

## 3. Errors

Failures are reported as one JSON object. The CLI writes it to stderr and exits
non-zero; the API returns it as the response body.

```json
{"error": "<kind>", "code": "<code>", "message": "<text>", "details": {}}
```

`details` is present only when the failure carries structured context.

| Kind | HTTP status | Meaning |
|---|---|---|
| `ValidationException` | 400 | well-formed request that violates a plane rule |
| `AccessDenied` | 403 | policy evaluation denied the request |
| `NotFound` | 404 | unknown repository, ref, pull request, or route |
| `GitError` | 500 | an underlying git invocation failed |

Codes used by graded behaviour:

| Code | Kind | Raised when |
|---|---|---|
| `UNKNOWN_PRINCIPAL` | `AccessDenied` | the caller is not in the principal catalog |
| `POLICY_DENY` | `AccessDenied` | evaluation ended in explicit or implicit deny |
| `MISSING_PRINCIPAL` | `ValidationException` | no principal was supplied at all |
| `APPROVAL_QUORUM` | `ValidationException` | a merge lacks counting approvals |
| `NOT_FAST_FORWARD` | `ValidationException` | the destination cannot fast-forward to the source |
| `NO_APPROVAL_RULE` | `ValidationException` | no approval rule covers the destination |
| `PR_NOT_FOUND` | `NotFound` | no such pull request |
| `PR_NOT_OPEN` | `ValidationException` | the pull request is already landed or closed |
| `REPO_NOT_FOUND` | `NotFound` | no such repository in the catalog |
| `REF_NOT_FOUND` | `NotFound` | the ref does not resolve |
| `DEST_EXISTS` | `ValidationException` | a clone destination path is already present |
| `PROTECTED_REF_MISSING` | `ValidationException` | a protected ref would be created by a push |

## 4. Operator commands

Global flags precede the subcommand: `--principal`, `--mfa`, `--no-mfa`,
`--source-ip`, `--pretty`. A successful command prints exactly one JSON object
on stdout. Fields below are the contracted shape; ordering of object keys in
command output is not significant.

| Command | Success object |
|---|---|
| `init` | `ok`, `root`, `repos[]` with `repo`, `head`, `protected` |
| `whoami` | `ok`, `version`, `principal`, `type`, `policies`, `statements`, `deny_statements` |
| `repos list` | `ok`, `count`, `repos[]` catalog entries |
| `repos refs REPO` | `ok`, `repo`, `default_branch`, `protected_refs`, `branches`, `head` |
| `clone REPO DEST` | `ok`, `repo`, `dest`, `ref`, `commit` |
| `push REPO WORKTREE BRANCH` | `ok`, `repo`, `ref` (full ref), `commit` (pushed object id) |
| `pr REPO --source S --dest D` | `ok`, `pr_id`, `pr` record |
| `approve REPO PR_ID` | `ok`, `pr_id`, `approvals` (sorted unique), `quorum` |
| `merge REPO PR_ID` | `ok`, `pr_id`, `repo`, `dest`, `source`, `commit`, `fast_forward`, `parents`, `approvals`, `rule_id` |
| `pr-status REPO PR_ID` | `ok`, `pr_id`, `repo`, `dest`, `dest_commit`, `source_commit`, `status`, `quorum` |
| `deliver REPO REF` | `ok`, `repo`, `ref` (full ref), `commit`, `duplicate`, `parked`, `delivered[]` |
| `journal [--repo R]` | `ok`, `count`, `rows[]` journal rows |
| `pipelines REPO` | `ok`, `repo`, `bindings[]`, `enabled` |
| `webhook outbox [--event E]` | `ok`, `count`, `summary`, `dead`, `rows[]` |
| `webhook dispatch --tick N` | `ok`, `tick`, `attempted`, `delivered[]`, `retried[]`, `dead[]`, `summary` |
| `audit query [filters]` | `ok`, `count`, `filters`, `summary`, `rows[]` |

`clone` requires `codecommit:GitPull`, `push` requires `codecommit:GitPush`,
`pr` requires `codecommit:CreatePullRequest`, `approve` requires
`codecommit:UpdatePullRequestApprovalState`, `merge` requires
`codecommit:MergePullRequestByFastForward`, `deliver` requires
`pipeline:StartPipelineExecution`, `webhook dispatch` requires
`webhook:DispatchOutbox`, `webhook outbox` requires `webhook:ListOutbox`, and
`audit query` requires `audit:QueryAuthzLog`. Repository-scoped actions
evaluate against that repository's ARN and, where the request names a ref,
against that ref. Plane-wide actions evaluate against repository `*`.

`audit query` filters are `--for-principal`, `--action`, `--repo`,
`--decision`, and `--limit`. Filters combine with AND and compare the
corresponding row field for equality. Rows come back in log order; `--limit`
caps how many are returned, keeping the earliest matches. The query's own
authorization is recorded before the log is read.

## 5. Approval rules and quorum

`ops/approval-rules.json` holds rules of `rule_id`, `repo`, `dest`,
`required`, and `pool`. A pull request is governed by the first rule whose
`repo` matches and whose `dest` covers the pull request destination, wildcards
allowed. A destination with no rule cannot be merged: `NO_APPROVAL_RULE`.

An approval counts toward quorum only when the approver is in the rule's
`pool`, is not the pull request author, and has not already been counted.
Repeat stamps from one principal are one vote. A stored pull request lists each
approver at most once. `required` is the rule's value; a merge attempt with
fewer counting approvals fails with `APPROVAL_QUORUM`.

The `quorum` object reports `rule_id`, `required`, `counted` (sorted counting
approvers), `ignored` (stamps present that do not count), `pool`, `satisfied`,
and `missing`.

## 6. Merge fence

`merge` proceeds in this order, and each step must pass before the next runs:

1. Resolve the pull request: `PR_NOT_FOUND`, then `PR_NOT_OPEN`.
2. Authorize `codecommit:MergePullRequestByFastForward` against the repository
   and the pull request destination ref.
3. Check quorum: `NO_APPROVAL_RULE` or `APPROVAL_QUORUM`.
4. Check the fence: the destination tip must be an ancestor of the pull
   request source commit. Otherwise `NOT_FAST_FORWARD`.
5. Advance the destination ref to the source commit.

A landed merge never creates a commit. After a successful merge the
destination ref equals the pull request's `source_commit`, the returned
`commit` is that same object id, `parents` is that commit's own parent list,
and `fast_forward` is true. The stored pull request moves to `status`
`merged` with `merged_commit` and `merged_by` set.

## 7. Pipeline delivery

`ops/pipelines.json` binds a `pipeline` to a `repo` and `ref` with an
`enabled` flag. `deliver` normalizes the requested ref, resolves that ref's
current tip, and starts every **enabled** binding for the pair. Disabled
bindings are reported in `parked` and never journalled.

A delivery is identified by

```
event_id = sha256("<repo>|<ref>|<commit>|<pipeline>") hex digest
```

where `<ref>` is the full ref. Delivery is exactly once per `event_id`: the
first delivery appends one journal row, and any later delivery of the same
repository, ref, commit, and pipeline appends nothing and reports the same
`event_id`. Because refs are normalized first, `main` and `refs/heads/main`
are the same delivery.

Each entry of `delivered[]` carries `pipeline`, `event_id`, and `duplicate`.
The top-level `duplicate` is true when at least one binding matched and every
matched binding was already journalled. A ref with no enabled binding delivers
nothing: `delivered` is empty, `duplicate` is false, and no journal row is
written.

## 8. Webhook outbox

`ops/webhooks.json` describes endpoints: `endpoint`, `url`, subscribed
`pipelines`, `max_attempts`, `backoff_base_ticks`, `reject_until_attempt`,
`enabled`, and `sink`.

Every delivery enqueues one outbox row per enabled subscribed endpoint.
Enqueue is idempotent: a `(event_id, endpoint)` pair has at most one row, so
repeating a delivery never adds a second row for the same pair. Rows start
`pending` with `attempts` 0 and `next_tick` 0.

`webhook dispatch --tick N` attempts every row that is `pending` and whose
`next_tick` is at or below `N`, in `outbox_id` order. Rows that are
`delivered` or `dead` are never attempted again.

The lab transport is a file sink. An attempt whose number is at or below the
endpoint's `reject_until_attempt` is refused; otherwise the attempt appends one
line to the endpoint's sink file and succeeds.

Attempt accounting, where `attempts` is the count after the attempt:

- success: `status` becomes `delivered`.
- failure with `attempts` below `max_attempts`: `status` stays `pending` and
  `next_tick` becomes `N + backoff_base_ticks * 2 ** (attempts - 1)`.
- failure with `attempts` at or above `max_attempts`: `status` becomes `dead`
  and no further attempt is made, so `attempts` never exceeds `max_attempts`.

## 9. State files

All state lives under `var/`. JSONL files are append-ordered, one object per
line, and their key order is part of the contract.

`var/catalog.json` — `{"repos": [...]}` with `name`, `arn`, `default_branch`,
`protected_refs`, `description`.

`var/repos/<name>.git` — bare repository per catalog entry.

`var/prs.json` — `{"next_id": <int>, "items": {"<pr_id>": <record>}}`. A
record holds `pr_id`, `repo`, `source`, `dest` (full refs), `author`,
`source_commit`, `base_commit`, `status`, `approvals` (sorted, unique),
`merged_commit`, `merged_by`, `created_at`, `title`.

`var/triggers.jsonl` — one row per journalled delivery, keys in exactly this
order:

```
["event_id", "repo", "ref", "commit", "pipeline", "status"]
```

`status` is `delivered` and `ref` is the full ref.

`var/audit.jsonl` — one row per evaluated request, keys in exactly this order:

```
["seq", "principal", "action", "repo", "ref", "decision", "reason", "source_ip", "mfa"]
```

`seq` starts at 1 and increases by one per row. `action` is the fully
qualified action name and is present on allow and deny rows alike. `ref` is
the full ref or null when the request named none. `decision` is `allow` or
`deny`. `reason` is one of `allowed_by_policy`, `explicit_deny`,
`no_matching_allow`, `unknown_principal`. `source_ip` is the supplied address
or null. `mfa` is a boolean.

`var/outbox.jsonl` — one row per queued endpoint delivery, keys in exactly
this order:

```
["outbox_id", "event_id", "endpoint", "pipeline", "repo", "ref", "commit", "status", "attempts", "next_tick"]
```

`outbox_id` starts at 1. `status` is `pending`, `delivered`, or `dead`.

`var/sinks/<endpoint>.jsonl` — lines written by successful attempts.

State survives restarts: a later command reads what an earlier command wrote,
and repeating an idempotent operation after a restart does not duplicate it.

## 10. HTTP surface

`bin/cc-api --host H --port P` serves the routes below and prints
`{"ok": true, "host": ..., "port": ...}` on stdout once bound; `--port 0`
selects a free port. `cc.api.app.handle(method, target, headers, body)` is the
router entry point and returns `(status, object)`.

| Method | Path | Body / query | Result |
|---|---|---|---|
| GET | `/api/v1/health` | — | `ok`, `service`, `version`; no identity needed |
| GET | `/api/v1/repos` | — | readable catalog entries |
| GET | `/api/v1/repos/{repo}/refs` | — | same object as `repos refs` |
| POST | `/api/v1/repos/{repo}/push` | `worktree`, `branch` | same object as `push` |
| GET | `/api/v1/prs` | `?repo=` | `ok`, `count`, `prs[]` |
| POST | `/api/v1/prs` | `repo`, `source`, `dest` | same object as `pr` |
| GET | `/api/v1/prs/{id}` | — | `ok`, `pr`, `quorum` |
| POST | `/api/v1/prs/{id}/approvals` | — | same object as `approve` |
| POST | `/api/v1/prs/{id}/merge` | — | same object as `merge` |
| POST | `/api/v1/pipelines/deliver` | `repo`, `ref` | same object as `deliver` |
| GET | `/api/v1/pipelines/journal` | `?repo=` | `ok`, `count`, `rows[]`, `bindings[]` |
| GET | `/api/v1/audit` | `?principal=&action=&repo=&decision=&limit=` | same object as `audit query` |
| GET | `/api/v1/webhooks/outbox` | `?event=` | same object as `webhook outbox` |
| POST | `/api/v1/webhooks/dispatch` | `tick` | same object as `webhook dispatch` |

The HTTP surface is not a second policy. For the same identity, MFA
assertion, source address, and arguments, a route reaches the same decision
and the same state change as the equivalent CLI command, including the
recorded decision row. A request with no principal header on a route that
needs one fails `MISSING_PRINCIPAL`; a principal that is not in the catalog is
denied `UNKNOWN_PRINCIPAL` like anywhere else.
