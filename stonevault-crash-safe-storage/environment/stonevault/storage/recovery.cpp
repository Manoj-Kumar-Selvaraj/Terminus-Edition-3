#include "recovery.hpp"

#include <algorithm>
#include <cstdint>
#include <limits>
#include <stdexcept>

namespace stonevault {

namespace {

std::uint64_t safe_next_transaction_id(std::uint64_t max_tx_id) {
    if (max_tx_id == std::numeric_limits<std::uint64_t>::max()) {
        throw std::runtime_error(
            "WAL corruption: transaction id space exhausted");
    }
    return std::max<std::uint64_t>(1, max_tx_id + 1);
}

void apply_recovered_commits(
    const RecoveryResult& recovery,
    VersionCatalog& catalog,
    std::uint64_t& commit_sequence) {
    for (const RecoveredCommit& commit : recovery.commits) {
        if (commit.sequence != commit_sequence + 1) {
            throw std::runtime_error(
                "WAL corruption: recovered sequence gap");
        }
        catalog.apply_commit(commit.writes, commit.sequence);
        commit_sequence = commit.sequence;
    }
}

}  // namespace

RecoveredDatabase restore_database(
    SnapshotStore& snapshots,
    WalManager& wal,
    VersionCatalog& catalog) {
    snapshots.remove_stale_temporary();

    const SnapshotImage snapshot = snapshots.load();
    catalog.load_snapshot(snapshot);
    std::uint64_t sequence = snapshot.sequence;

    const RecoveryResult recovery = wal.recover(sequence);
    apply_recovered_commits(recovery, catalog, sequence);

    return RecoveredDatabase{
        sequence,
        safe_next_transaction_id(recovery.max_tx_id),
    };
}

}  // namespace stonevault
