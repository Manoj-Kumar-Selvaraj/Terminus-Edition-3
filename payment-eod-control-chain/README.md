# Payment EOD control chain

## Difficulty rationale

This task condenses the source payment EOD documentation into the part of the lifecycle where replay safety and financial integrity interact. A plausible fix to duplicate detection can still fail on restart, a correct restart can still publish an unreconciled clearing population, and balanced ledger totals alone do not prove population completeness. The intended difficulty comes from tracing one payment through COBOL decisions, SQL state transitions, shell orchestration, accounting, reconciliation, completion, and rerun behavior.

## Solution approach

The oracle keeps COBOL as the owner of duplicate and execution decisions, makes SQL financial effects idempotent, and changes the shell controller so publication and success are gated by authoritative reconciliation/completion state. Exact accepted source-reference replays are duplicates; commercial similarity is not sufficient. Existing authoritative postings or reservations are resumed rather than repeated.

## Verification approach

The verifier rebuilds the database for independent scenarios, compiles and runs the submitted COBOL programs through the submitted shell controller, and validates observable database and artifact semantics. Hidden-style cases include exact replay versus legitimate recurring activity, clean internal/external execution, insufficient funds, rerunning a completed cycle, resuming pre-existing financial effects, balanced accounting, population completeness, and a completion prerequisite that blocks success authorization.

## Source-document mapping

The modeled scope is taken from the uploaded functional suite rather than invented as a generic batch. DUP090 supplies exact-replay versus recurring-payment semantics; INT130 supplies atomic internal posting; EXT140 and CLR150 supply reservation-before-clearing and one-authorized-population controls; GLG180/GLP200 supply balanced accounting recognition; REC210 supplies population, response, clearing and ledger reconciliation; CTL270 supplies completion prerequisites; and OK280 supplies the single downstream success authorization. Earlier STG010 through RSK080 responsibilities are represented as already-authorized input preconditions so the exercise stays focused.
