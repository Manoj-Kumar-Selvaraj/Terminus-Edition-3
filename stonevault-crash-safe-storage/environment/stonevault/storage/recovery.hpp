#pragma once

#include "catalog.hpp"
#include "snapshot.hpp"
#include "wal.hpp"

#include <cstdint>

namespace stonevault {

struct RecoveredDatabase {
    std::uint64_t commit_sequence{};
    std::uint64_t next_transaction_id{1};
};

RecoveredDatabase restore_database(
    SnapshotStore& snapshots,
    WalManager& wal,
    VersionCatalog& catalog);

}  // namespace stonevault
