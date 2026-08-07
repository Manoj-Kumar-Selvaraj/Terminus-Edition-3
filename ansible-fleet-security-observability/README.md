# ansible-fleet-security-observability

## What the task is

A single-host fleet harden lab with three logical edge instance roots
(`/app/edges/app`, `/app/edges/data`, `/app/edges/ops`) and a control seal under
`/app/var/fleet-harden`. Ansible roles chain eleven interdependent stages
(inventory → packages → patch stamp → auditd → metrics → promtail → falco →
firewall → ssh → scrape mesh → posture seal), install offline adapter listeners
for security/monitoring tooling, and publish a posture report.

Adapters form a live observability chain: audit serves a derived `chain_token`,
promtail `/ready` must fetch that token from audit, and falco `/healthz` must
expose a `wire` carrying the token plus cross ports. Package seals, stage gates,
templates/handlers, and agreeing-wrong role defaults raise the inference load.

The shipped playbooks look operational but disagree with the contract on
interacting axes (stamp source, scrape CIDR, swapped roles including ops,
firewall, SSH, promtail↔audit wiring, falco cross-ports, soft stage gates,
incomplete package seal, scrape host order). Goals live in `instruction.md`.
Layouts and schemas live in the hand-written contract
`environment/docs/posture-contract.md` and the audit handoff under
`environment/evidence/`.

## Validation

```bash
IS_SANDBOX=1 ./terminus3.sh oracle ansible-fleet-security-observability
IS_SANDBOX=1 ./terminus3.sh nop ansible-fleet-security-observability
IS_SANDBOX=1 ./terminus3.sh check-llm ansible-fleet-security-observability
```
