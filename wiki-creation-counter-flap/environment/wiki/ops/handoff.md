# wiki oncall

Postgres (here: the wiki sqlite file) disappeared for ~8 minutes. Ready flipped 503. Someone set liveness to the ready URL so kube would "notice." Both pods restarted. Grafana `creation-dashboard-678` now shows ~0 creates; `SELECT count(*) FROM users` is still thousands.

Please stop coupling live to the database, and make `/metrics` agree with the tables after the file comes back. Two processes — scrape both.

— Priya
