# terraform-aws-claims-edge-exception-cutover

Edition 3 migration of the CloudFront/WAF origin-lockdown theme into a live
HTTP edge lab. The scored work is per-request routing, cache-key isolation,
signed-path exceptions, and origin authorization — not canary weight or DNS
promotion (see `terraform-live-edge-canary-cutover` for that surface).

## Why it is hard

Path precedence, cache policy, signed access, origin headers, WAF rate windows,
and logging must stay consistent across three distributions. A plan that looks
right but routes or caches incorrectly fails live probes.

## Verification

Separate verifier rebuilds Terraform plans from submitted modules (including
hidden inventory variants), starts the edge lab, and grades HTTP behavior plus
cutover evidence. Oracle and NOP use the same path.

## Base image

Canonical Python 3.13 slim bookworm (digest-pinned). Terraform and the AWS
provider mirror are baked at build time for offline plan generation.
