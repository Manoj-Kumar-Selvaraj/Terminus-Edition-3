* Harden the three fleet edges rooted at /app/edges/app, /app/edges/data, and /app/edges/ops. The current Ansible under /app/environment/ansible is broken. 

* Run the finished work through /app/bin/fleet-harden-apply and keep control state under /app/var/fleet-harden.

* Run hardening stages in order on each edge, followed by scrape and seal on the control host. 

* A stage cannot report success until the one before it has completed.

* Each edge inventory must carry its hostname, role, adapter ports, and the chain token derived from the engagement map.

* Install and seal the required packages. Use the real engagement stamp from the evidence during the patch window, not the decoy.

* Allow metrics through the firewall only from the scrape CIDR. 

* Deny other sources. Disable SSH password login and tighten root access and login attempts.

* Bring up working audit, metrics, log-shipping, and runtime-sensing adapters on every edge. Metrics labels must match the inventory role.

* Wire Promtail to the local audit bridge. Its /ready response must carry the live audit chain token. Falco rules and health must cite the cross ports and expose an observability wire with that same token.

* Build the scrape mesh from the live inventories in inventory order. Do not hardcode roles or chain tokens, and do not reorder hosts.

* A second apply must succeed and leave the same live state and valid contract evidence.

* Leave /app/var/fleet-harden/scrape/targets.json and /app/var/fleet-harden/posture-report.json. 

* The posture report must echo the engagement controls and satisfy the required seal fields.

* Read the stage map, ports, token formula, config shapes, scrape schema, and report shape from /app/environment/evidence/ and /app/environment/docs/posture-contract.md. 

* Do not change the contract to fit the playbooks.

