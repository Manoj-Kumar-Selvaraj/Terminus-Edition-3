#pragma once

#include "catalog.hpp"
#include "maintenance.hpp"
#include "transactions.hpp"

#include <cstdint>
#include <string>

namespace stonevault {

struct StoragePathAudit {
    bool lock_present{};
    bool wal_present{};
    bool snapshot_present{};
    bool snapshot_temporary_present{};
    std::uint64_t lock_bytes{};
    std::uint64_t wal_bytes{};
    std::uint64_t snapshot_bytes{};
    std::uint64_t snapshot_temporary_bytes{};
};

struct RuntimeAudit {
    CatalogAudit catalog;
    TransactionAudit transactions;
    StoragePathAudit storage;
};

struct IntegrityReport {
    std::uint64_t commit_sequence{};
    std::uint64_t visible_keys{};
    std::uint64_t active_transactions{};
    std::uint64_t wal_bytes{};
    bool snapshot_present{};
};

CatalogAudit validate_catalog_integrity(
    const VersionCatalog& catalog,
    std::uint64_t commit_sequence);

TransactionAudit validate_transaction_integrity(
    const TransactionTable& transactions,
    std::uint64_t commit_sequence);

StoragePathAudit validate_storage_paths(const StoragePaths& paths);

RuntimeAudit audit_runtime_state(
    const StoragePaths& paths,
    const VersionCatalog& catalog,
    const TransactionTable& transactions,
    std::uint64_t commit_sequence);

std::string render_health(const IntegrityReport& report);

}  // namespace stonevault
