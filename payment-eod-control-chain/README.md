# Payments EOD batch control

This repository contains the overnight payment settlement controller used by the CORP-ACH batch path. The shell controller coordinates COBOL decision programs, SQLite holds durable batch and financial state, and the files under `out/` are publication or operator artifacts derived from that state.

The current incident started during the 2026-08-08 EOD window after the run host stopped between financial stages. Operations kept the run and restart logs under `environment/eod/log/archive/` and left a short handoff under `environment/eod/ops/`. Those artifacts are the quickest way to understand what was already durable when the retry started.

The restart rules and independent COBOL interfaces are documented under `environment/eod/docs/`. The important operational distinction is between work that is already authoritative in the database and work that is only missing downstream continuation. A restart may therefore need to retain a posting or reservation, rebuild a later accounting/clearing step, or hold the cycle when durable state no longer agrees with the payment.

Reconciliation and close are separate controls. A balanced cycle may publish the customer and clearing files; authorization is later and depends on close prerequisites. The database is the recovery authority throughout the run.
