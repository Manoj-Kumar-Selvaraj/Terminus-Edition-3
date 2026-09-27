# Local collection lab

The lab simulates a bounded set of synthetic live endpoints and reports capability, plan acceptance, attempt status, and generated synthetic payload descriptors. It offers deterministic dispatch, status lookup, cancellation, and callback recording. It never opens a connection to a real endpoint or requires a credential.

The fixed seed and case/endpoint/source identities determine generated metadata and payload bytes. The lab may simulate unavailable sources, partial acquisition, delayed observations, and restart-visible acknowledgements through its configured scenario state. These are ordinary local service outcomes, not external network faults. Offline intake uses the same result envelope and identity checks without requiring a running lab request.
