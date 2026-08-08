# Payment EOD restart control

This task presents a restart defect in a legacy payment EOD chain built from small COBOL decision programs, a shell controller and SQLite durable state. The happy path is intentionally less important than the partially completed states: the batch has to distinguish a replay from recurring business, resume authoritative postings/reservations, preserve capacity and accounting semantics, and keep publication/close gates tied to reconciliation.

The environment is arranged the way an operations-facing batch package commonly is: the controller and libraries live under `bin/` and `lib/`, COBOL decisions under `cobol/`, SQL state under `sql/`, and a few short operating/interface notes under `docs/`. Those notes describe the existing business controls and record contracts; they are not a solution walkthrough.

The reference repair treats the database as the restart authority, makes financial effects unique at the database boundary, and reconstructs only missing downstream state when the durable effect itself is consistent. Reconciliation is cycle-scoped and checks population, financial-effect, reservation/clearing and ledger invariants. Publication is withheld on a held reconciliation, while completion additionally requires delivery, report and archive prerequisites.

The verifier uses independent database scenarios rather than source inspection. Fail-to-pass cases cover replay identity, resumed postings/reservations, payer capacity, atomic internal execution, reservation-before-clearing, accounting completeness, reconciliation isolation, held publication, close prerequisites and repeated completed runs. Pass-to-pass cases protect stable output/interface behavior.
