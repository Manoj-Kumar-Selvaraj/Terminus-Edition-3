# EC2 artifact policy enforcement focused hardening

This note records the focused verifier-hardening pass for the existing `ec2-artifact-policy-enforcement` task.

Scope is intentionally limited to cross-surface enforcement consistency and non-overridable safety invariants already present in the solver-visible contract:

- untrusted container registries must be denied;
- direct dependency-manager acquisition paths (`pip`, `npm`) must use the same source policy as Maven;
- vulnerability exceptions cannot override source trust, missing immutable digest, scanner unavailability, or stale scanner evidence;
- permits remain bound to request ID, instance ID, artifact digest, policy version, expiry, and keyed signature;
- allow/deny decisions remain durable and the most recent decision survives normal process restart.

No new product subsystem, policy category, fleet-provisioning behavior, or hidden implementation requirement is introduced by this hardening pass.
