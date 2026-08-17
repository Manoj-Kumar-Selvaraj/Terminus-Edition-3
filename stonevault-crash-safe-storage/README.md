# Crash-safe embedded storage hardening

This task is a cross-language storage-engine reliability work package. The inherited system has a Rust command/control plane and a C++20 durable storage core split across transaction, MVCC catalog, WAL, recovery, snapshot, locking, integrity and maintenance responsibilities. The starter remains buildable and usable on basic happy paths, but several coupled durability/isolation/maintenance invariants are incomplete.

The intended repair is not a rewrite: preserve the public line protocol, C ABI and on-disk formats while restoring writer fencing, MVCC visibility, atomic conflict handling, transactional recovery, corruption classification, checkpoint lifecycle and operator observability. The verifier drives the compiled executable as an external process and perturbs durable files to exercise restart and failure semantics.

Difficulty is expected to come from causal coupling: fixes in recovery affect sequence/state visibility; checkpoint behavior affects recovery and observability; transaction visibility interacts with scans and conflict arbitration; writer lifecycle and health reporting depend on resource ownership. The final empirical tier still requires the repository's official model-trial workflow and is not established by this README.
