# 8 Aug ~21:00 shopdesk

AZ-A disk filled. Orchestration said AZ-B is writer. I would not put the LB back on AZ-A `/readyz` yet.

What we actually saw:

- AZ-B gunicorn still logging `db=replica` on POST /api/checkout/place
- shopper shp-4412 paid, hit confirmation on the other box, cart still OPEN
- capture vendor got att-inc-20001 / 20007 / 20012 twice (once per app box)
- someone ran a half-finished copy job toward standby and the lease row showed up over there writable

Files:

- `/app/ha/state/primary.sqlite` — still thinks it can write
- `/app/ha/state/standby.sqlite` — behind, and not actually read-only
- `/app/ha/logs/captured/shopdesk-error.log`
- `/app/ha/docs/runbook.md`

Please do not rebuild schema or rename the checkout URLs. `/readyz` has to mean “safe to take a card”, not “gunicorn is up”.
