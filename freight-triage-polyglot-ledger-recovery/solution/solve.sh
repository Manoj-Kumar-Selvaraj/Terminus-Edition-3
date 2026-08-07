#!/usr/bin/env bash
# Repair the three freight services so they agree with
# /app/environment/docs/requirements.md, then run the suite.
#
# Corrected sources live under /solution/fixed with the same layout as
# /app/environment; each one is dropped in place of the broken original.
set -euo pipefail

FIXED=/solution/fixed
ENVROOT=/app/environment

install_fixed() {
    local relative="$1"
    install -m 0644 "$FIXED/$relative" "$ENVROOT/$relative"
}

# C++ ledger engine: freight epoch, SHA-256 word order, CRC-32 seal digest byte
# order, seal upper casing, band lower edge, kilogram exact slot capacity with
# one based slots and priority first ordering, empty manifests carried through,
# snapshot ordered by lane then arrival.
install_fixed native/src/sha256.cpp
install_fixed native/src/crc.cpp
install_fixed native/src/timeutil.cpp
install_fixed native/src/manifest.cpp
install_fixed native/src/tariff.cpp
install_fixed native/src/allocator.cpp
install_fixed native/src/ledger.cpp

# Java intake: offset qualified timestamps, upper cased seals hashed with
# CRC-32/ISO-HDLC, fletcher32 modulus, holds counted once, hold rows named
# manifest_id and ordered by it, replay in seq order.
install_fixed intake/src/com/freight/util/FreightTime.java
install_fixed intake/src/com/freight/util/SealDigest.java
install_fixed intake/src/com/freight/hash/Fletcher32.java
install_fixed intake/src/com/freight/intake/HoldStore.java
install_fixed intake/src/com/freight/intake/JournalWriter.java
install_fixed intake/src/com/freight/intake/ReplayClient.java

# Go reconciler: freight epoch, manifest_id hold field, half open windows,
# half up accrual, distinct slot counting, audit ordering, LF CSV with the
# contracted column order, zigzag round trip.
install_fixed reconcile/internal/timeutil/timeutil.go
install_fixed reconcile/internal/model/model.go
install_fixed reconcile/internal/audit/audit.go
install_fixed reconcile/internal/report/report.go
install_fixed reconcile/internal/codecx/zigzag_byte.go

rm -rf /app/output
rm -rf "$ENVROOT/native/build" "$ENVROOT/intake/build" "$ENVROOT/reconcile/build"

/app/bin/run-freight-suite --root /app
