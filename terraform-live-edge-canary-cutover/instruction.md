1) Repair the weekend edge cutover on this host. The live control plane listens on 127.0.0.1:8787, keeps state under /app/var/edge, and already has traffic flowing.
2) The Terraform under /app/environment/terraform must move that plane through networks, pools, WAF, TLS, canary traffic, DNS, observability, and the traffic guard. It is not in a good state right now.
3) Use /app/bin/edge-cutover-apply to build and start the plane from /app/environment/edgectl, apply Terraform, and leave the plane running.
4) Read the fleet from /app/environment/terraform/inventory/edge-fleet.auto.tfvars.json and the binding rules from /app/environment/docs/cutover-contract.md. Work out the phase order, module wiring, and safety gates from those files. Do not edit the contract to match the current modules.
5) Wire the root module through the contracted child modules in order: networks, pools, WAF and TLS, canary steps, DNS, observatory, then traffic guard.
6) Compose engagement, route, network, pool, WAF, and TLS IDs from the inventory. Do not invent new ones.
7) Raise canary traffic only through the listed steps. Both pools must be healthy, and the live error budget must stay within its limit while weight moves.
8) Put WAF into enforce and install the inventory TLS material for the edge hostname before DNS cutover.
9) Change DNS to green only after the canary reaches its final step and WAF is enforcing.
10) After cutover, the observatory and traffic guard must still see live metrics inside budget. A seal that looks right while live error rate is blown is not enough.
11) Leave /app/var/edge/cutover-seal.json and /app/var/edge/snapshot.json. The seal must satisfy the contract seal fields against inventory. The snapshot must be the live control-plane state at seal time and agree with the seal on canary weight, WAF mode, TLS fingerprint and hostname, and DNS target.
12) A second apply must succeed under live metrics and leave the seal consistent with the new snapshot.
