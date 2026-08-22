# Policy Contract

Published policy versions are immutable. Their digest covers canonical policy content, detector bundle, key epoch, allowlists, suppressions, thresholds, and budgets. Jobs copy version and digest and never follow a mutable alias.

Allowlist and suppression entries have tenant, category, source or department scope, normalized fingerprint matcher, policy version, reason, and optional UTC expiry. The narrowest matching active rule wins; expired or differently scoped entries do not suppress. Detector confidence and positive or negative context are evaluated before suppression and publication.

The fingerprint key is derived for tenant, scan scope, policy key epoch, and category. Raw candidates, reversible encodings, unkeyed hashes, and globally comparable keys are forbidden. Masking is category-aware and deterministic but never reveals more than a safe suffix or structural punctuation, including short values.