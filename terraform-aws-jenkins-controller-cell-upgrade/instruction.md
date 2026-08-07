Last week's controller-cell plugin bump left the CI fleet in a bad place: one shared home claim, mixed plugin provenance, and jobs that jumped cells when a controller restarted.

 We need three isolated Jenkins controller cells — payments, risk, and platform — with separate identities, storage, scheduling, routing, and job ownership. 
 
 There is no Operations Center object here; the fleet registry under `/app/cells` is the source of truth for cell membership and job assignment.

Inventory and topology live under `/app/data`; the failed upgrade notes are in `/app/evidence`. The cell contract is `/app/docs/cell-upgrade-contract.md`. 

Repair Terraform under `/app/terraform` and the cell deploy config under `/app/cells`, then run `/app/bin/cell-upgrade`. 

That command must regenerate `/app/var/cells/plan.json`, materialize the three cells under `/app/var/cells`, exercise job routing, restart one controller, run a failed upgrade on one cell while the others keep serving, and leave `/app/output/cell-upgrade-report.json` with status `READY`. 

Plugin provenance must gate boot, homes must stay exclusive (no dual writers), build numbers must survive restart and rollback, and node disruption rules must keep sibling cells available. 

A second identical run must keep the same report digest.
