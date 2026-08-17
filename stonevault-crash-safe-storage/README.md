# StoneVault crash-safe storage task

This Terminus Edition-3 task presents a small native transactional database whose happy path works but whose production invariants have regressed. The agent repairs the existing C++20 storage core and Rust command layer in `/app/stonevault` while preserving the public line protocol and binary disk formats.

The task is intentionally cross-layer. Correctness depends on WAL recovery, snapshot isolation, write/write conflict detection, deterministic bytewise scans, corruption classification, atomic checkpoint semantics, process-level writer exclusion, and restart-safe statistics. The starter is functional enough that shallow smoke testing is misleading.

## Language boundary

Product implementation is C++ and Rust only. Python is confined to the separate verifier image. The verifier also checks that no Python or Go implementation files appear in the submitted product tree.

## Grading shape

The verifier drives the compiled native CLI as an external process and exercises fresh databases, restarts, killed sessions, overlapping transactions, binary data, WAL perturbations, checkpoint/restart cycles, and competing writers. It does not inspect implementation branches or require a particular repair strategy beyond the stated language and public-format constraints.
