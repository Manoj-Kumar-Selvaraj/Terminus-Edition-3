# terraform-live-edge-canary-cutover

## What the task is

A live edge canary cutover lab (~11k lines of HCL + ~3k lines of Go). A Go
control plane (`edgectl`) accepts network, pool, WAF, TLS, canary and DNS
updates while synthetic traffic is already running. Terraform modules under
`/app/environment/terraform` must walk the inventory canary steps in order and
only cut DNS to green after weight 100, WAF enforce, healthy pools and matching
TLS — then seal `/app/var/edge/cutover-seal.json`.

The shipped Terraform looks almost right but violates interacting gates
(early DNS, detect-mode WAF, skipped canary steps, bad TLS fingerprint,
loose traffic guard). Goals in `instruction.md`; shapes in
`environment/docs/cutover-contract.md`.

## Defects (broken tree)

1. WAF left in `detect` (DNS cutover requires `enforce`).
2. TLS fingerprint does not match inventory.
3. Canary steps jump to 100 before walking 10/25/50/75.
4. DNS module not `depends_on` canary completion.
5. Traffic guard budget / wiring softened.

## Validation

```bash
IS_SANDBOX=1 ./terminus3.sh oracle terraform-live-edge-canary-cutover
IS_SANDBOX=1 ./terminus3.sh nop terraform-live-edge-canary-cutover
IS_SANDBOX=1 ./terminus3.sh check-llm terraform-live-edge-canary-cutover
```
