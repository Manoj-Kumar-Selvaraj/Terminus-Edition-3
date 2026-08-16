# Shift note — settlement source control

Handing over mid-incident. Read this with `log/authz.jsonl` open.

## What we saw

Thursday 14:20 the settlement team reported that a change landed on ledger
mainline that nobody remembers approving. Working backwards from the decision
extract in `log/authz.jsonl`:

- Alice's mainline push at 14:07 was allowed. She was on the guest wifi and had
  not touched her token that day. Prod refuses that combination.
- The same change shows one reviewer stamp, then a merge, while mainline had
  already moved twice since her branch point. Mainline's history now has a
  commit that is not in either branch.
- The intern account cloned and then pushed. Onboarding accounts are supposed to
  be clone-only until week three.
- `settle-prod` ran twice against the same head. Finance saw two settlement
  files for one cycle and had to reverse one by hand.
- Security asked for every denied decision for the intern account and got a list
  that included rows for other accounts.

## What we changed

Nothing in `ops/` or `policies/`. The attachments in there are the ones
security signed off in March, and the pool in `approval-rules.json` is current.
Treat that configuration as correct and the plane's behaviour as suspect.

We did point the lab at its own root while poking at it — export `CC_ROOT` to a
scratch directory and you get an isolated copy without touching the shared one.
`ccctl init` bootstraps a fresh root.

## Where the platform team got to

Also worth knowing: the API went in after the CLI, on a deadline, and the two
surfaces have not been compared side by side since. Ops drive the API from their
runbooks now, so whatever the CLI enforces the API needs to enforce too.

The webhook mirror is new. `audit-mirror` has been unreachable since the
security VPC move, which is expected for now — what is not expected is the
retry queue growing without bound.

Next shift: reconcile behaviour with `docs/control-plane-contract.md`. That
document is what prod implements.
