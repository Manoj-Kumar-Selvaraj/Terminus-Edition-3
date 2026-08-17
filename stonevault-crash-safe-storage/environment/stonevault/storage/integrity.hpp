#pragma once

#include "catalog.hpp"
#include "maintenance.hpp"

#include <cstdint>
#include <string>

namespace stonevault {

struct IntegrityReport {
    std::uint64_t commit_sequence{};
    std::uint64_t visible_keys{};
    std::uint64_t active_transactions{};
    std::uint64_t wal_bytes{};
    bool snapshot_present{};
};

void validate_catalog_integrity(
    const VersionCatalog& catalog,
    std::uint64_t commit_sequence);

void validate_storage_paths(const StoragePaths& paths);

std::string render_health(const IntegrityReport& report);

}  // namespace stonevault
